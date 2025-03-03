import os
import glob
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv(dotenv_path=".env")

api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(openai_api_key=api_key, model='chatgpt-4o-latest', temperature=0)

dirname = os.path.dirname(__file__)
tailOfInputPath = "/input_files/unibw/TwoWay"
tailOfOutputPath = "/generated_text_files/unibw/TwoWay"
inputDir = str(dirname) + str(tailOfInputPath)
textOutputDir = str(dirname) + str(tailOfOutputPath)

def read_puml_files(directory):
    uml_files = glob.glob(os.path.join(directory, "*.puml"))
    if not uml_files:
        raise FileNotFoundError("No .puml files found in the directory")

    model_data = []
    for file_path in uml_files:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            filename = os.path.basename(file_path)
            model_data.append((filename, content))

    return model_data

def read_xmi_files(directory):
    uml_files = glob.glob(os.path.join(directory, "*.xmi"))
    if not uml_files:
        raise FileNotFoundError("No .xmi files found in the directory")

    model_data = []
    for file_path in uml_files:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            filename = os.path.basename(file_path)
            model_data.append((filename, content))

    return model_data

def save_description(description, output_directory, filename):
    """Saves the generated description to the output directory with the same filename but .txt extension."""
    os.makedirs(output_directory, exist_ok=True)
    output_file = os.path.join(output_directory, os.path.splitext(filename)[0] + ".txt")
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(description)

def read_system_message():
    prompt_file_path = os.path.join(dirname, "query_scripts", "prompts", "encoder_prompt_system_message.txt")
    with open(prompt_file_path, "r", encoding="utf-8") as file:
        system_message = file.read()
    return system_message

def read_task_description():
    prompt_file_path = os.path.join(dirname, "query_scripts", "prompts", "encoder_prompt_task_description.txt")
    with open(prompt_file_path, "r", encoding="utf-8") as file:
        task_description = file.read()
    return task_description

def main():
    model_data = read_xmi_files(inputDir)
    system_message = read_system_message()
    task_description = read_task_description()

    prompt_template = PromptTemplate(
        template="""{system_message}
{task_description}: {file_content}""",
        input_variables=["system_message", "task_description", "file_content"],
    )

    for fn_ct in model_data:
        filename = fn_ct[0]
        file_content = fn_ct[1]
        chain = prompt_template | llm
        print_prompt = prompt_template.invoke({
            "system_message": system_message,
            "task_description": task_description,
            "file_content": file_content
        })
        print(print_prompt.to_string())
        answer = chain.invoke({
            "system_message": system_message,
            "task_description": task_description,
            "file_content": file_content
        })
        save_description(answer.content, textOutputDir, filename)

if __name__ == "__main__":
    main()
