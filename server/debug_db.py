import models
from database import engine, SessionLocal
import os

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    cols = db.query(models.ColumnModel).all()
    print(f"Columns in DB: {len(cols)}")
    for c in cols:
        print(f" - {c.id}: {c.name}")
        
    if len(cols) == 0:
        print("Preloading columns...")
        init_path = os.path.join(os.path.dirname(__file__), "init.json")
        import json
        if os.path.exists(init_path):
            with open(init_path, 'r') as f:
                config = json.load(f)
                for col_data in config.get("columns", []):
                    if isinstance(col_data, str):
                        name = col_data
                        order = 0
                        agent = None
                    else:
                        name = col_data.get("name")
                        order = col_data.get("order", 0)
                        agent = col_data.get("default_agent_id")
                    db.add(models.ColumnModel(name=name, order=order, default_agent_id=agent))
            db.commit()
            print("Success (from init.json)!")
        else:
            default_columns = ["Idea", "Design", "Development", "QA", "Done"]
            for idx, name in enumerate(default_columns):
                db.add(models.ColumnModel(name=name, order=idx))
            db.commit()
            print("Success (default values)!")
finally:
    db.close()
