import os
import time

from modal import Image, Secret, Stub, method

MODEL_DIR = "/model"
BASE_MODEL = "TheBloke/Mistral-7B-Instruct-v0.1-AWQ"

def download_model_to_folder():
    from huggingface_hub import snapshot_download
    from transformers.utils import move_cache

    os.makedirs(MODEL_DIR, exist_ok=True)

    snapshot_download(
        BASE_MODEL,
        local_dir=MODEL_DIR,
        token=os.environ["HF_TOKEN"],
    )
    move_cache()


image = (
    Image.from_registry(
        "nvidia/cuda:12.1.0-base-ubuntu22.04", add_python="3.10"
    )
    .pip_install("vllm==0.2.5", "huggingface_hub==0.19.4", "hf-transfer==0.1.4")
    # Use the barebones hf-transfer package for maximum download speeds. No progress bar, but expect 700MB/s.
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(
        download_model_to_folder,
        secret=Secret.from_name("my-huggingface-secret"),
        timeout=60 * 20,
    )
)

stub = Stub("mistral-7b-awq", image=image)  


@stub.cls(gpu="a100", secret=Secret.from_name("my-huggingface-secret"))
class Model:
    def __enter__(self):
        from vllm import LLM

        # Load the model. Tip: MPT models may require `trust_remote_code=true`.
        self.llm = LLM(MODEL_DIR, quantization="AWQ", dtype="float16")
        self.template = """<s>[INST] <<SYS>>
{system}
<</SYS>>

{user} [/INST] """

    @method()
    def generate(self, user_questions):
        from vllm import SamplingParams

        prompts = [
            self.template.format(system="", user=q) for q in user_questions
        ]

        sampling_params = SamplingParams(
            # temperature=0.75,
            # top_p=1,
            max_tokens=2000,
            # presence_penalty=1.15,
        )
        start = time.time()
        result = self.llm.generate(prompts, sampling_params)
        num_tokens = 0
        tokens = []
        for output in result:
            num_tokens += len(output.outputs[0].token_ids)
            print(output.prompt, output.outputs[0].text, "\n\n", sep="")
        print(f"Generated {num_tokens} tokens")

        elapsed = time.time() - start
        print(
            f"[DONE] {num_tokens} tokens generated in {elapsed:.2f}s ({num_tokens / elapsed:.0f} tok/s)"
        )


@stub.local_entrypoint()
def main():
    model = Model()
    questions = [
        # Coding questions
        # "Implement a Python function to compute the Fibonacci numbers.",
        # "Write a Rust function that performs binary exponentiation.",
        # "How do I allocate memory in C?",
        # "What are the differences between Javascript and Python?",
        # "How do I find invalid indices in Postgres?",
        # "How can you implement a LRU (Least Recently Used) cache in Python?",
        # "What approach would you use to detect and prevent race conditions in a multithreaded application?",
        # "Can you explain how a decision tree algorithm works in machine learning?",
        # "How would you design a simple key-value store database from scratch?",
        # "How do you handle deadlock situations in concurrent programming?",
        # "What is the logic behind the A* search algorithm, and where is it used?",
        # "How can you design an efficient autocomplete system?",
        # "What approach would you take to design a secure session management system in a web application?",
        # "How would you handle collision in a hash table?",
        # "How can you implement a load balancer for a distributed system?",
        # # Literature
        # "What is the fable involving a fox and grapes?",
        # "Write a story in the style of James Joyce about a trip to the Australian outback in 2083, to see robots in the beautiful desert.",
        # "Who does Harry turn into a balloon?",
        # "Write a tale about a time-traveling historian who's determined to witness the most significant events in human history.",
        # "Describe a day in the life of a secret agent who's also a full-time parent.",
        # "Create a story about a detective who can communicate with animals.",
        # "What is the most unusual thing about living in a city floating in the clouds?",
        # "In a world where dreams are shared, what happens when a nightmare invades a peaceful dream?",
        # "Describe the adventure of a lifetime for a group of friends who found a map leading to a parallel universe.",
        # "Tell a story about a musician who discovers that their music has magical powers.",
        # "In a world where people age backwards, describe the life of a 5-year-old man.",
        # "Create a tale about a painter whose artwork comes to life every night.",
        # "What happens when a poet's verses start to predict future events?",
        # "Imagine a world where books can talk. How does a librarian handle them?",
        # "Tell a story about an astronaut who discovered a planet populated by plants.",
        # "Describe the journey of a letter traveling through the most sophisticated postal service ever.",
        # "Write a tale about a chef whose food can evoke memories from the eater's past.",
        # # History
        # "What were the major contributing factors to the fall of the Roman Empire?",
        # "How did the invention of the printing press revolutionize European society?",
        # "What are the effects of quantitative easing?",
        # "How did the Greek philosophers influence economic thought in the ancient world?",
        # "What were the economic and philosophical factors that led to the fall of the Soviet Union?",
        # "How did decolonization in the 20th century change the geopolitical map?",
        # "What was the influence of the Khmer Empire on Southeast Asia's history and culture?",
        # Thoughtfulness
        "Describe the city of the future, considering advances in technology, environmental changes, and societal shifts.",
        # "In a dystopian future where water is the most valuable commodity, how would society function?",
        # "If a scientist discovers immortality, how could this impact society, economy, and the environment?",
        # "What could be the potential implications of contact with an advanced alien civilization?",
        # # Math
        # "What is the product of 9 and 8?",
        # "If a train travels 120 kilometers in 2 hours, what is its average speed?",
        # "Think through this step by step. If the sequence a_n is defined by a_1 = 3, a_2 = 5, and a_n = a_(n-1) + a_(n-2) for n > 2, find a_6.",
        # "Think through this step by step. Calculate the sum of an arithmetic series with first term 3, last term 35, and total terms 11.",
        # "Think through this step by step. What is the area of a triangle with vertices at the points (1,2), (3,-4), and (-2,5)?",
        # "Think through this step by step. Solve the following system of linear equations: 3x + 2y = 14, 5x - y = 15.",
        # # Facts
        # "Who was Emperor Norton I, and what was his significance in San Francisco's history?",
        # "What is the Voynich manuscript, and why has it perplexed scholars for centuries?",
        # "What was Project A119 and what were its objectives?",
        # "What is the 'Dyatlov Pass incident' and why does it remain a mystery?",
        # "What is the 'Emu War' that took place in Australia in the 1930s?",
        # "What is the 'Phantom Time Hypothesis' proposed by Heribert Illig?",
        # "Who was the 'Green Children of Woolpit' as per 12th-century English legend?",
        # "What are 'zombie stars' in the context of astronomy?",
        # "Who were the 'Dog-Headed Saint' and the 'Lion-Faced Saint' in medieval Christian traditions?",
        # "What is the story of the 'Globsters', unidentified organic masses washed up on the shores?",

 
    ]
    num_tokens = model.generate.remote(questions)


