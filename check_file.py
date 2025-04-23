def check_file(filename, start_line, num_lines):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i in range(start_line - 1, min(start_line - 1 + num_lines, len(lines))):
        line_num = i + 1
        line = lines[i].rstrip('\n')
        print(f"{line_num}: {repr(line)}")

def find_and_print_function(filename, func_name, context=50):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if func_name in line and 'def ' in line:
            start = max(0, i - 2)
            end = min(len(lines), i + context)
            print(f"Found {func_name} at line {i+1}, showing lines {start+1}-{end}:")
            for j in range(start, end):
                print(f"{j+1}: {repr(lines[j].rstrip())}")
            return
    
    print(f"Function {func_name} not found")

if __name__ == "__main__":
    check_file('app.py', 1208, 5) 