import sys
import os
# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock required variables
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["JWT_SECRET_KEY"] = "supersecretkey"

try:
    from app.core.config import Settings
    import pydantic
    print(f"Pydantic Version: {pydantic.VERSION}")
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def test_config():
    print("Testing default settings...")
    try:
        defaults = Settings(_env_file=None)
        print(f"Default ALLOWED_HOSTS: {defaults.ALLOWED_HOSTS}")
    except Exception as e:
        print(f"Defaults failed: {e}")

    print("\nTesting JSON env vars...")
    os.environ["ALLOWED_HOSTS"] = '["json.com", "works.com"]'
    os.environ["BACKEND_CORS_ORIGINS"] = '["http://json.com"]'
    try:
        json_settings = Settings()
        print(f"JSON ALLOWED_HOSTS: {json_settings.ALLOWED_HOSTS}")
    except Exception as e:
        print(f"JSON failed: {e}")

    print("\nTesting Comma-Separated env vars...")
    os.environ["ALLOWED_HOSTS"] = "foo.com,bar.com"
    os.environ["BACKEND_CORS_ORIGINS"] = "http://foo.com,http://bar.com"
    
    try:
        custom = Settings()
        print(f"Parsed ALLOWED_HOSTS: {custom.ALLOWED_HOSTS}")
        print(f"Parsed BACKEND_CORS_ORIGINS: {custom.BACKEND_CORS_ORIGINS}")
        
        assert "foo.com" in custom.ALLOWED_HOSTS
        assert len(custom.ALLOWED_HOSTS) == 2
        print("\n✅ Verification SUCCESS")
    except Exception as e:
        print(f"Comma failed: {e}")
        # Print full traceback if needed
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_config()
