import os
from redis import Redis
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
redis_client = Redis(host=REDIS_HOST, port=6379, decode_responses=True)

DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True )
    completed = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)
app = FastAPI()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
@app.get("/")
def read_root():
    count = redis_client.incr("visits")
    return {"message": "FastAPI and Redis are connected!", "visitor_count": count}

@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    return db.query(Task).all()

@app.post("/tasks")
def add_task(task_name: str, db: Session = Depends(get_db)):
    task = Task(name=task_name, completed=False)
    db.add(task)
    db.commit()
    db.refresh(task)
    redis_client.rpush("task_queue" , task.id)
    return {"message": "Task added successfully and added to queue", "task": task_name}

@app.get("/tasks/queue")
def view_queue():
    tasks_in_queue = redis_client.lrange("task_queue", 0, -1)
    return {"queue": tasks_in_queue}

@app.post("/tasks/process-next")
def process_next_task(db: Session = Depends(get_db)):
    task_id = redis_client.lpop("task_queue")
    if task_id:
        task = db.query(Task).filter(Task.id == int(task_id)).first()
        if task:
            task.completed = True
            db.commit()
            return {"message": "Task processed successfully", "task": task.name}
        else:
            return {"message": "Task not found in database", "task_id": task_id}
    else:
        return {"message": "No tasks in the queue"}

@app.delete("/tasks/{task_id}")
def delete_task(task_id:int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
        return {'message': 'Task deleted successfully', 'task': task.name}
    else:
        return {'message': 'Task not found', 'task_id': task_id}