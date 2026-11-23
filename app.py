import httpx

from core.ai_engine import AIEngine
from core.tools import TOOLS, keyword_matches, run_tool
from services.downloads import DownloadsService

HELP = "Just ask naturally (news, downloads status, most visited sites...). Type exit to close."


def main():
    ai = AIEngine()

    print("=" * 45)
    print("       MY PERSONAL AI ASSISTANT")
    print("=" * 45)
    print(f"AI Model: {ai.model} (runs locally, data never leaves your PC)")
    print(HELP)
    print("-" * 45)

    try:  # startup warning if Downloads is huge
        warning = DownloadsService().summary()["warning"]
        if warning:
            print(f"\n[!] {warning}")
    except FileNotFoundError as e:
        print(f"\n[!] {e}")

    descriptions = {name: t[0] for name, t in TOOLS.items()}

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() == "exit":
            break
        if not user_input:
            continue

        print("\nAssistant: Thinking...")
        # One clear keyword match -> no model call needed (small models misroute).
        # Several matches -> the model chooses among them; none -> model decides from all tools.
        matches = keyword_matches(user_input)
        if len(matches) == 1:
            tool = matches[0]
        else:
            pool = {n: descriptions[n] for n in matches} or descriptions
            tool = ai.route(user_input, pool)

        tool_data = None
        if tool:
            print(f"[using tool: {tool}]")
            try:
                tool_data = run_tool(tool)
            except (httpx.HTTPError, OSError) as e:
                tool_data = f"The tool failed: {e}"

        print("\nAssistant:", ai.chat(user_input, tool_data))


if __name__ == "__main__":
    main()
