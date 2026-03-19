import argparse

from rllm import RLM

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-guards", action="store_true", help="Disable depth and iteration guards"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress intermediate output"
    )
    args = parser.parse_args()

    prompt = "Explain to me the overall architecture of this library and what key insights should i take for building my own c libraries, i'm passing a C header file to you in your environment!"
    contents = ""
    with open("./example/nob.h", "r") as f:
        contents = f.read()

    print(f"Context Length: {len(contents)}")

    model = RLM(
        initial_prompt=prompt,
        initial_context=contents,
        max_depth=5,
        disable_guards=args.no_guards,
        quiet=args.quiet,
    )
    model.run(max_iter=100)
