import ollama

class Summarizer:
    def __init__(self, model="llama3"):
        self.model = model

    def summarize(self, transcript):
        if not transcript.strip():
            return "No conversation captured."
        
        # Enhanced prompt to force a summary even for short clips
        prompt = f"""Analyze and summarize the following conversation segment.

### INSTRUCTIONS:
- Even if the transcript is very short or contains casual chatter, do NOT say "there is nothing to summarize."
- Instead, describe the TOPIC or NATURE of the interaction (e.g., "A brief greeting," "Concluding a discussion," "Testing audio levels," or "Casual small talk").
- If specific decisions or action items are present, list them.
- If it's a monologue, summarize the main point being made.

### TRANSCRIPT:
{transcript}

### SUMMARY:"""
        try:
            response = ollama.chat(model=self.model, messages=[
                {
                    'role': 'system',
                    'content': 'You are a persistent administrative assistant. You always provide a brief description of the context or topic of a conversation, no matter how short or sparse the transcript is.',
                },
                {
                    'role': 'user',
                    'content': prompt,
                },
            ])
            return response['message']['content'].strip()
        except Exception as e:
            return f"Error generating summary: {e}"
