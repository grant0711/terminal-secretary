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
- **IMPORTANT**: If there are any tasks or action items for the user, list them explicitly on their own lines using the format: `- [ACTION]: description of task`
- If it's a monologue, summarize the main point being made.

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
