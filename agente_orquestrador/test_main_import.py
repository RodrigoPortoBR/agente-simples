try:
    import main
    print("Imported main successfully")
except Exception as e:
    print(f"Error importing main: {e}")
    import traceback
    traceback.print_exc()
