from core.ai_engine import AIEngine

def main():

    ai = AIEngine()

    print("=" * 45)
    print("       MY PERSONAL AI ASSISTANT")
    print("=" * 45)
    print("AI Model: Gemma 3 1B")
    print("Type 'exit' to close.")
    print("-" * 45)

    while True:
        user_input = input("\nYou:").strip()

        if user_input.lower() == "exit":
            break
        if not user_input:
            continue

        print("\nAssistant: Thinking...")

        answer = ai.chat(user_input)

        print("\nAssistant:", answer)


if __name__ == "__main__":
    main()