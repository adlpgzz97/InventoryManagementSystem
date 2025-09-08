from backend.app import create_app
from backend.utils.database import execute_query

app = create_app()
with app.app_context():
    try:
        # Check what tables exist
        result = execute_query(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%stock%'
            """,
            fetch_all=True
        )
        print('Stock-related tables:')
        for row in result:
            print(f'  - {row["table_name"]}')
    except Exception as e:
        print(f'Error: {e}')
