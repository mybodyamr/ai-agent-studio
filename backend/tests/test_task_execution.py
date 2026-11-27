import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app.config import settings
from app.db import connect, init_db
from app.main import execute_task

class TaskExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db_path=str(Path(self.tmp.name)/"tasks.sqlite3")
        self.patch=patch.object(settings,"database_path",self.db_path)
        self.patch.start()
        init_db()
        with connect() as db:
            db.execute("INSERT INTO tasks(id,title,status,agent) VALUES('t1','test','running','analyst')")
            db.commit()

    async def asyncTearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    async def test_task_persists_result(self):
        with patch("app.main.run_agent",new_callable=AsyncMock,return_value="completed"):
            await execute_task("t1")
        with connect() as db:
            row=db.execute("SELECT status,result FROM tasks WHERE id='t1'").fetchone()
            self.assertEqual(row["status"],"done")
            self.assertEqual(row["result"],"completed")

    async def test_cancelled_task_records_cancelled_status(self):
        started=asyncio.Event()
        async def wait_forever(*args,**kwargs):
            started.set()
            await asyncio.Event().wait()
        with patch("app.main.run_agent",side_effect=wait_forever):
            job=asyncio.create_task(execute_task("t1"))
            await started.wait()
            job.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await job
        with connect() as db:
            row=db.execute("SELECT status FROM tasks WHERE id='t1'").fetchone()
            self.assertEqual(row["status"],"cancelled")

if __name__ == "__main__":
    unittest.main()
