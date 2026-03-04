"""
Terminal chat interface — interact with each agent directly in your terminal.
No cloud account or browser needed.

    uv run python chat.py

Pick an agent from the menu, then chat with it. Type 'exit' to quit,
'menu' to switch agents.
"""
import sys
from pathlib import Path

# Allow imports from project root when run from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))


def ensure_output_dirs():
    for d in ["outputs/discovery", "outputs/qualified", "outputs/research", "outputs/pdfs"]:
        Path(d).mkdir(parents=True, exist_ok=True)


def main():
    ensure_output_dirs()

    from agents.discovery import create_discovery_agent
    from agents.qualifier import create_qualifier_agent
    from agents.researcher import create_researcher_agent

    agents = {
        "1": ("Discovery Agent", create_discovery_agent),
        "2": ("Qualifier Agent", create_qualifier_agent),
        "3": ("Researcher Agent", create_researcher_agent),
    }

    def print_menu():
        print("\n" + "=" * 50)
        print("  Harlem Grown Prospect Intelligence")
        print("=" * 50)
        for key, (name, _) in agents.items():
            print(f"  {key}. {name}")
        print("  q. Quit")
        print("=" * 50)

    print_menu()

    current_agent = None
    current_name = None

    while True:
        if current_agent is None:
            choice = input("\nSelect agent (1/2/3) or q to quit: ").strip().lower()
            if choice == "q":
                print("Goodbye.")
                sys.exit(0)
            if choice not in agents:
                print("Invalid choice.")
                continue
            current_name, factory = agents[choice]
            print(f"\nStarting {current_name}... (type 'menu' to switch agents, 'exit' to quit)\n")
            current_agent = factory()

        current_agent.cli_app(
            stream=True,
            markdown=True,
            exit_on=["exit", "menu", "quit"],
        )

        # After cli_app exits, check if user typed 'menu' or 'exit'
        current_agent = None
        current_name = None
        print_menu()


if __name__ == "__main__":
    main()
