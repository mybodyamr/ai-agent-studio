import uuid
import asyncio
import re
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import connect, init_db
from .schemas import ChatRequest, MemoryRequest, ResearchRequest, TaskRequest, SkillCreate, SkillUpdate
from .agents import AGENTS
from .ollama import status as ollama_status
from .orchestrator import run_agent
from .research import search_public_web
from .files import safe_path, extract_text, workspace, validate_file_content
from .skills import list_skills, select_skills

app=FastAPI(title="AI Agent Studio API", version="0.2.0")
worker_task: asyncio.Task | None = None
current_execution: asyncio.Task | None = None
current_task_id: str | None = None
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin,"http://127.0.0.1:3000"], allow_credentials=False, allow_methods=["GET","POST","PATCH","DELETE"], allow_headers=["Content-Type"])

@app.on_event("startup")
async def startup():
    global worker_task
    init_db()
    with connect() as db:
        db.execute("UPDATE tasks SET status='queued',updated_at=CURRENT_TIMESTAMP WHERE status='running'")
        db.commit()
    worker_task=asyncio.create_task(task_worker())

@app.on_event("shutdown")
async def shutdown():
    global worker_task
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        worker_task=None

def audit(db, event, entity_id=None, detail=None):
    db.execute("INSERT INTO audit_events(event,entity_id,detail) VALUES(?,?,?)",(event,entity_id,detail))

@app.get("/api/health")
async def health():
    return {"ok":True,"ollama":await ollama_status(),"agents":len(AGENTS),"storage":"local","version":"0.2.0"}

@app.get("/api/agents")
def agents():
    return [{"id":k,**v} for k,v in AGENTS.items()]

@app.get("/api/skills")
def get_skills():
    with connect() as db:
        return list_skills(db)

@app.post("/api/skills")
def create_skill(req: SkillCreate):
    skill_id = "custom-" + uuid.uuid4().hex[:12]
    with connect() as db:
        db.execute(
            "INSERT INTO skills(id,name,description,instructions,triggers,enabled,builtin) VALUES(?,?,?,?,?,1,0)",
            (skill_id, req.name, req.description, req.instructions, json.dumps(req.triggers, ensure_ascii=False))
        )
        audit(db, "skill.created", skill_id, req.name)
        db.commit()
        return next(skill for skill in list_skills(db) if skill["id"] == skill_id)

@app.patch("/api/skills/{skill_id}")
def update_skill(skill_id: str, req: SkillUpdate):
    with connect() as db:
        cur = db.execute("UPDATE skills SET enabled=? WHERE id=?", (int(req.enabled), skill_id))
        if not cur.rowcount:
            raise HTTPException(404, "Skill not found")
        audit(db, "skill.enabled" if req.enabled else "skill.disabled", skill_id)
        db.commit()
        return next(skill for skill in list_skills(db) if skill["id"] == skill_id)

@app.delete("/api/skills/{skill_id}")
def delete_skill(skill_id: str):
    with connect() as db:
        row = db.execute("SELECT builtin,name FROM skills WHERE id=?", (skill_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Skill not found")
        if row["builtin"]:
            raise HTTPException(403, "Built-in skills cannot be deleted; you can disable them.")
        db.execute("DELETE FROM skills WHERE id=?", (skill_id,))
        audit(db, "skill.deleted", skill_id, row["name"])
        db.commit()
        return {"deleted": True}

@app.get("/api/conversations")
def conversations():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM conversations ORDER BY updated_at DESC LIMIT 100")]

@app.get("/api/conversations/{cid}")
def get_conversation(cid: str):
    with connect() as db:
        conv=db.execute("SELECT * FROM conversations WHERE id=?",(cid,)).fetchone()
        if not conv: raise HTTPException(404,"Conversation not found")
        msgs=db.execute("SELECT role,content,agent,created_at FROM messages WHERE conversation_id=? ORDER BY id",(cid,)).fetchall()
        return {"conversation":dict(conv),"messages":[dict(m) for m in msgs]}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    agent=req.agent if req.agent in AGENTS else "manager"
    cid=req.conversation_id or str(uuid.uuid4())
    with connect() as db:
        exists=db.execute("SELECT id FROM conversations WHERE id=?",(cid,)).fetchone()
        if not exists:
            db.execute("INSERT INTO conversations(id,title) VALUES(?,?)",(cid,req.message[:60]))
        else:
            db.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(cid,))
        history=db.execute("SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 16",(cid,)).fetchall()
        history=list(reversed(history))
        memories=db.execute("SELECT content FROM memories WHERE project='default' ORDER BY id DESC LIMIT 8").fetchall()
        terms=re.findall(r"[\w\u0600-\u06ff]{3,}",req.message.lower())[:8]
        file_context=""
        if terms:
            fts_query=" OR ".join(f'"{term}"' for term in terms)
            try:
                excerpts=db.execute("SELECT original_name,snippet(documents_fts,2,'','',' … ',24) AS excerpt FROM documents_fts WHERE documents_fts MATCH ? LIMIT 3",(fts_query,)).fetchall()
                file_context="\n\n".join("File: "+row["original_name"]+"\n"+row["excerpt"] for row in excerpts)
            except Exception:
                file_context=""
        available_skills = list_skills(db, enabled_only=True)
        selected_skills = select_skills(req.message, available_skills)
        db.execute("INSERT INTO messages(conversation_id,role,content,agent) VALUES(?,?,?,?)",(cid,"user",req.message,agent))
        db.commit()
    try:
        answer=await run_agent(agent,req.message,[{"role":m["role"],"content":m["content"]} for m in history],[m["content"] for m in memories],file_context,selected_skills)
    except Exception:
        raise HTTPException(503,"تعذر الاتصال بـ Ollama. تأكد من تشغيله وتثبيت النموذج المحلي المحدد.")
    with connect() as db:
        db.execute("INSERT INTO messages(conversation_id,role,content,agent) VALUES(?,?,?,?)",(cid,"assistant",answer,agent))
        db.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(cid,))
        audit(db,"chat.completed",cid,agent)
        db.commit()
    return {"conversation_id":cid,"answer":answer,"agent":agent,"skills":[{"id":skill["id"],"name":skill["name"]} for skill in selected_skills]}

@app.get("/api/memory")
def list_memory(project: str="default"):
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM memories WHERE project=? ORDER BY id DESC",(project,))]

@app.post("/api/memory")
def add_memory(req: MemoryRequest):
    with connect() as db:
        cur=db.execute("INSERT INTO memories(project,content) VALUES(?,?)",(req.project,req.content))
        audit(db,"memory.created",str(cur.lastrowid),req.project)
        db.commit()
        return {"id":cur.lastrowid,"saved":True}

@app.delete("/api/memory/{memory_id}")
def delete_memory(memory_id: int):
    with connect() as db:
        cur=db.execute("DELETE FROM memories WHERE id=?",(memory_id,))
        if not cur.rowcount: raise HTTPException(404,"Memory not found")
        audit(db,"memory.deleted",str(memory_id))
        db.commit()
        return {"deleted":True}

@app.get("/api/memory/search")
def search_memory(q: str, project: str="default"):
    if not q.strip() or len(q)>200: raise HTTPException(400,"Invalid search query")
    with connect() as db:
        try:
            rows=db.execute("SELECT m.id,m.project,m.content,m.created_at FROM memories_fts f JOIN memories m ON m.id=f.rowid WHERE memories_fts MATCH ? AND m.project=? ORDER BY rank LIMIT 20",(q,project)).fetchall()
        except Exception:
            raise HTTPException(400,"Search query syntax is invalid")
        return [dict(r) for r in rows]

@app.post("/api/research")
async def research(req: ResearchRequest):
    try:
        return {"query":req.query,"results":await search_public_web(req.query),"privacy":"Only the explicitly entered query is sent externally."}
    except Exception:
        raise HTTPException(502,"External research is temporarily unavailable.")

async def execute_task(tid: str):
    try:
        with connect() as db:
            row=db.execute("SELECT * FROM tasks WHERE id=? AND status='running'",(tid,)).fetchone()
            if not row:
                return
            title,detail,agent=row["title"],row["detail"] or "",row["agent"]
            memories=db.execute("SELECT content FROM memories WHERE project='default' ORDER BY id DESC LIMIT 8").fetchall()
            selected_skills = select_skills(f"{title}\n{detail}", list_skills(db, enabled_only=True))
        result=await run_agent(agent,f"{title}\n\n{detail}",[],[r["content"] for r in memories],skills=selected_skills)
        with connect() as db:
            cur=db.execute("UPDATE tasks SET status='done',result=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='running'",(result,tid))
            if cur.rowcount:
                audit(db,"task.completed",tid)
            db.commit()
    except asyncio.CancelledError:
        with connect() as db:
            cur=db.execute("UPDATE tasks SET status='cancelled',updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='running'",(tid,))
            if cur.rowcount:
                audit(db,"task.cancelled",tid)
            db.commit()
        raise
    except Exception as exc:
        with connect() as db:
            db.execute("UPDATE tasks SET status='failed',error=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='running'",(str(exc)[:1000],tid))
            audit(db,"task.failed",tid)
            db.commit()

async def task_worker():
    global current_execution, current_task_id
    while True:
        try:
            with connect() as db:
                row=db.execute("SELECT id FROM tasks WHERE status='queued' ORDER BY created_at,id LIMIT 1").fetchone()
                if row:
                    tid=row["id"]
                    claimed=db.execute("UPDATE tasks SET status='running',updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='queued'",(tid,))
                    db.commit()
                    if not claimed.rowcount:
                        tid=None
                else:
                    tid=None
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(1)
            continue
        if not tid:
            await asyncio.sleep(0.75)
            continue
        current_task_id=tid
        current_execution=asyncio.create_task(execute_task(tid))
        try:
            await current_execution
        except asyncio.CancelledError:
            if asyncio.current_task() and asyncio.current_task().cancelling():
                raise
        except Exception:
            await asyncio.sleep(1)
        finally:
            current_execution=None
            current_task_id=None

@app.get("/api/tasks")
def tasks():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM tasks ORDER BY created_at DESC")]

@app.post("/api/tasks")
def add_task(req: TaskRequest):
    tid=str(uuid.uuid4())
    agent=req.agent if req.agent in AGENTS else "manager"
    with connect() as db:
        queued=db.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('queued','running')").fetchone()[0]
        if queued>=100: raise HTTPException(429,"Task queue is full. Wait for current tasks to finish.")
        db.execute("INSERT INTO tasks(id,title,detail,agent) VALUES(?,?,?,?)",(tid,req.title.strip(),req.detail,agent))
        audit(db,"task.created",tid,agent)
        db.commit()
    return {"id":tid,"title":req.title.strip(),"status":"queued"}

@app.post("/api/tasks/{tid}/cancel")
async def cancel_task(tid: str):
    with connect() as db:
        cur=db.execute("UPDATE tasks SET status='cancelled',updated_at=CURRENT_TIMESTAMP WHERE id=? AND status IN ('queued','running')",(tid,))
        if not cur.rowcount: raise HTTPException(409,"Task is already finished or missing")
        audit(db,"task.cancelled",tid)
        db.commit()
    if current_task_id==tid and current_execution and not current_execution.done():
        current_execution.cancel()
    return {"cancelled":True}

@app.get("/api/files")
def list_files():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT id,original_name,characters,created_at FROM documents ORDER BY created_at DESC")]

@app.post("/api/files")
async def upload_file(file: UploadFile=File(...)):
    original=(file.filename or "upload.txt").replace("\\","/").split("/")[-1][:240]
    try:
        path=safe_path(original)
    except ValueError as exc:
        raise HTTPException(400,str(exc))
    data=await file.read(10_000_001)
    if len(data)>10_000_000: raise HTTPException(413,"File exceeds 10 MB limit")
    try:
        validate_file_content(original,data)
        path.write_bytes(data)
        content=extract_text(path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(400,str(exc))
    did=str(uuid.uuid4())
    try:
        with connect() as db:
            db.execute("INSERT INTO documents(id,original_name,stored_name,characters) VALUES(?,?,?,?)",(did,original,path.name,len(content)))
            db.execute("INSERT INTO documents_fts(document_id,original_name,content) VALUES(?,?,?)",(did,original,content))
            audit(db,"file.uploaded",did,original)
            db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise HTTPException(500,"تعذر حفظ فهرس الملف محليًا.")
    return {"id":did,"name":original,"characters":len(content),"preview":content[:3000]}

@app.get("/api/files/search")
def search_files(q: str):
    if not q.strip() or len(q)>200: raise HTTPException(400,"Invalid search query")
    with connect() as db:
        try:
            rows=db.execute("SELECT document_id,original_name,snippet(documents_fts,2,'<b>','</b>','…',16) AS excerpt FROM documents_fts WHERE documents_fts MATCH ? ORDER BY rank LIMIT 20",(q,)).fetchall()
        except Exception:
            raise HTTPException(400,"Search query syntax is invalid")
        return [dict(r) for r in rows]

@app.get("/api/files/{document_id}")
def read_file(document_id: str):
    with connect() as db:
        row=db.execute("SELECT * FROM documents WHERE id=?",(document_id,)).fetchone()
    if not row: raise HTTPException(404,"File not found")
    path=workspace()/Path(row["stored_name"]).name
    if not path.is_file() or path.parent!=workspace(): raise HTTPException(404,"File data is missing")
    try:
        content=extract_text(path)
    except Exception:
        raise HTTPException(500,"Unable to read local file")
    return {"id":document_id,"name":row["original_name"],"content":content}

@app.delete("/api/files/{document_id}")
def delete_file(document_id: str):
    with connect() as db:
        row=db.execute("SELECT * FROM documents WHERE id=?",(document_id,)).fetchone()
        if not row: raise HTTPException(404,"File not found")
        db.execute("DELETE FROM documents WHERE id=?",(document_id,))
        db.execute("DELETE FROM documents_fts WHERE document_id=?",(document_id,))
        audit(db,"file.deleted",document_id,row["original_name"])
        db.commit()
    (workspace()/Path(row["stored_name"]).name).unlink(missing_ok=True)
    return {"deleted":True}

@app.get("/api/activity")
def activity():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT 100")]
