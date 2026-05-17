from src import bronze, gold
from src.silver import run as silver_run
from src import generate_dashboard

if __name__ == "__main__":
    print("=== BRONZE ===")
    bronze.run()
    print("\n=== SILVER ===")
    silver_run()
    print("\n=== GOLD ===")
    gold.run()
    print("\n=== DASHBOARD ===")
    generate_dashboard.main()
    print("\nPipeline concluído.")
