# models/llm/generator.py

from transformers import pipeline
import torch


class LLMGenerator:

    def __init__(self):

        device = 0 if torch.cuda.is_available() else -1

        self.generator = pipeline(
            "text-generation",
            model="mistralai/Mistral-7B-Instruct-v0.2",
            device=device
        )

    def generate(self, prompt, max_tokens=300):

        output = self.generator(
            prompt,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7
        )

        return output[0]["generated_text"]
