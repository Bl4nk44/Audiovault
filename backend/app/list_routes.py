
from app.main import app

def list_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "name": route.name,
                "methods": list(route.methods)
            })
    
    # Sort by path
    routes.sort(key=lambda x: x["path"])
    
    for r in routes:
        print(f"{r['methods']} {r['path']} -> {r['name']}")

if __name__ == "__main__":
    list_routes()
