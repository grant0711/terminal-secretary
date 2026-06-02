import ollama

class Summarizer:
    def __init__(self, model="llama3"):
        self.model = model

    def summarize(self, transcript):
        if not transcript.strip():
            return "No conversation captured."
        
        # Enhanced prompt to force a summary and explicit action items
        prompt = f"""Analyze and summarize the following conversation segment.

### INSTRUCTIONS:
- Even if the transcript is very short or contains casual chatter, do NOT say "there is nothing to summarize."
- Instead, describe the TOPIC or NATURE of the interaction (e.g., "A brief greeting," "Concluding a discussion," "Testing audio levels," or "Casual small talk").
- If specific decisions or action items are present, list them.
- **IMPORTANT**: You MUST identify tasks, action items, and "notes to self". 
- Explicitly include **scheduling meetings**, **reaching out to people**, and **reminders** as tasks.
- Format every task on its own line exactly like this: `- [ACTION]: description of task`
- Examples of tasks to extract: 
    - `- [ACTION]: Schedule meeting with Doug and Clinton to discuss interaction model`
    - `- [ACTION]: Follow up with Li Shon regarding the feedback loop`
    - `- [ACTION]: Research GPU acceleration for Docker`

### TRANSCRIPT:
{transcript}

### SUMMARY:"""
        try:
            response = ollama.chat(model=self.model, messages=[
                {
                    'role': 'system',
                    'content': 'You are a persistent administrative assistant. You always provide a brief description of the context or topic of a conversation and identify actionable tasks using the format "- [ACTION]: task".',
                },
                {
                    'role': 'user',
                    'content': prompt,
                },
            ])
            return response['message']['content'].strip()
        except Exception as e:
            return f"Error generating summary: {e}"

    def generate_review(self, conversations, timeframe):
        """Generates a synthesized review of multiple conversations."""
        if not conversations:
            return f"No conversations found for {timeframe}."

        context = "\n\n".join([f"Time: {c[1]}\nSummary: {c[2]}" for c in conversations])
        
        prompt = f"""Below is a series of summaries from conversations recorded {timeframe}. 
Please provide a high-level review of what was accomplished, key themes, and any outstanding loose ends that should be prioritized.

### CONVERSATION SUMMARIES:
{context}

### SYNTHESIZED REVIEW:"""
        
        try:
            response = ollama.chat(model=self.model, messages=[
                {
                    'role': 'system',
                    'content': 'You are a professional administrative assistant providing a retrospective review of work activities.',
                },
                {
                    'role': 'user',
                    'content': prompt,
                },
            ])
            return response['message']['content'].strip()
        except Exception as e:
            return f"Error generating review: {e}"
