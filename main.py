from rllm import RLM

if __name__ == "__main__":
    prompt = "Analyze this library by sections. For each section of the code, identify the main functionality and how it works. Then combine all sections into a comprehensive summary."

    contents = ""
    with open("./example/nob.h", "r") as f:
        contents = f.read()

    print(f"Context Length: {len(contents)}")

    model = RLM(initial_prompt=prompt, initial_context=contents, max_depth=2)
    model.run(max_iter=100)
