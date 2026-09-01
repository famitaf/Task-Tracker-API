from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

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
tasks = []
@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    return db.query(Task).all()

@app.post("/tasks")
def add_task(task_name: str, db: Session = Depends(get_db)):
    task = Task(name=task_name, completed=False)
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"message": "Task added successfully", "task": task_name}
@app.post("/tasks/process-next")
def process_next_task(db: Session = Depends(get_db)):
    next_task = db.query(Task).filter(Task.completed == False).order_by(Task.id.asc()).first()
    if next_task:
        next_task.completed = True
        db.commit()
        db.refresh(next_task)
        return {"message": "Processed task successfully", "task": next_task.name}
    else:
        return {"message": "No pending tasks"}

@app.delete("/tasks/{task_id}")
def delete_task(task_id:int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
        return {'message': 'Task deleted successfully', 'task': task.name}
    else:
        return {'message': 'Task not found', 'task_id': task_id}