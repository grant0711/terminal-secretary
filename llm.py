import ollama
import os

class Summarizer:
    def __init__(self, model="llama3"):
        self.model = model
        self.think = os.getenv("OLLAMA_THINK", "true").lower() == "true"

    def summarize(self, transcript):
        if not transcript.strip():
            return "No conversation captured."
        
        # Refined prompt for speaker-aware summaries and task extraction
        prompt = f"""You are analyzing a transcript from a professional environment. The speakers are labeled as [ME] (the user, Grant) and [OTHERS] (colleagues). 

Your goal is to provide a comprehensive record of the discussion and extract clear, punchy action items specifically for Grant.

### CORE OBJECTIVES:
1.  **Detailed Summary**: Provide a thorough overview of the conversation. Capture key arguments, technical details, context, and the flow of discussion between [ME] and [OTHERS].
2.  **Grant's Action Items**: Identify tasks, commitments, or follow-ups that Grant ([ME]) needs to perform.

### TASK EXTRACTION CRITERIA:
- **Include** a task if [ME] says they will do it (e.g., "[ME]: I'll take a look at that").
- **Include** a task if [OTHERS] explicitly assign it to Grant or ask Grant to do something (e.g., "[OTHERS]: Grant, can you update the docs?").
- **Exclude** tasks that [OTHERS] say they will do themselves (e.g., "[OTHERS]: I'll handle the deployment"). These should be in the summary but NOT in the Action Items.

### EXTRACTION RULES:
- **TASK FORMAT**: Every task must be on its own line starting exactly with `- [ACTION]: `.
- **CONCISENESS**: Keep the action items brief (one-sentence instructions).

### TRANSCRIPT:
\"\"\"{transcript}\"\"\"

### RESPONSE FORMAT:
**DETAILED SUMMARY**:
[Your thorough, detailed summary of the conversation]

**ACTION ITEMS**:
- [ACTION]: [Concise task for Grant]
"""
        try:
            response = ollama.chat(model=self.model, messages=[
                {
                    'role': 'system',
                    'content': 'You are a meticulous administrative assistant. You excel at distinguishing between speaker roles and identifying specific commitments made by or assigned to your user, Grant.',
                },
                {
                    'role': 'user',
                    'content': prompt,
                },
            ], think=self.think)
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
            ], think=self.think)
            return response['message']['content'].strip()
        except Exception as e:
            return f"Error generating review: {e}"
