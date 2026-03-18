from rllm import RLM

if __name__ == "__main__":
    prompt = "How do i use this library?"

    contents = ""
    with open("./example/nob.h", "r") as f:
        contents = f.read()

    print(f"Context Length: {len(contents)}")

    model = RLM(initial_prompt=prompt, initial_context=contents)
    model.run(max_depth=5)
