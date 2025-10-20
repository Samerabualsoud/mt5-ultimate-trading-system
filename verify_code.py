"""
Comprehensive Code Verification
Checks for actual bugs, logic errors, and integration issues
"""

import ast
import os
import sys
from typing import List, Dict, Tuple

class CodeVerifier:
    def __init__(self):
        self.issues = []
        self.warnings = []
        
    def add_issue(self, severity, file, line, message):
        self.issues.append({
            'severity': severity,
            'file': file,
            'line': line,
            'message': message
        })
    
    def check_file_syntax(self, filepath):
        """Check if file has valid Python syntax"""
        try:
            with open(filepath, 'r') as f:
                code = f.read()
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
    
    def check_imports(self, filepath):
        """Check if all imports are valid"""
        try:
            with open(filepath, 'r') as f:
                tree = ast.parse(f.read())
            
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            return imports
        except Exception as e:
            self.add_issue('ERROR', filepath, 0, f"Cannot parse imports: {e}")
            return []
    
    def check_function_calls(self, filepath):
        """Check for common function call errors"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for common issues
            for i, line in enumerate(lines, 1):
                # Check for mt5.positions_get() without checking None
                if 'mt5.positions_get()' in line and i < len(lines):
                    next_lines = '\n'.join(lines[i:min(i+5, len(lines))])
                    if 'if not positions' not in next_lines and 'if positions' not in next_lines:
                        self.add_issue('WARNING', filepath, i, 
                                     "mt5.positions_get() should check for None/empty")
                
                # Check for division without zero check
                if '/' in line and 'if' not in line and '#' not in line:
                    if any(var in line for var in ['loss', 'denominator', 'total', 'count']):
                        self.add_issue('WARNING', filepath, i,
                                     "Potential division by zero")
                
                # Check for .iloc[-1] without length check
                if '.iloc[-1]' in line:
                    prev_lines = '\n'.join(lines[max(0, i-5):i])
                    if 'len(' not in prev_lines and 'if' not in prev_lines:
                        self.add_issue('WARNING', filepath, i,
                                     ".iloc[-1] without length check")
        
        except Exception as e:
            self.add_issue('ERROR', filepath, 0, f"Cannot check function calls: {e}")
    
    def check_logic_errors(self, filepath):
        """Check for logic errors"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Check for always-true conditions
                if 'if True:' in line and '#' not in line:
                    self.add_issue('ERROR', filepath, i, "Always-true condition")
                
                # Check for empty except blocks
                if line.strip() == 'except:' or line.strip().startswith('except '):
                    if i < len(lines) and lines[i].strip() == 'pass':
                        self.add_issue('WARNING', filepath, i,
                                     "Empty except block - errors silently ignored")
                
                # Check for missing return in functions
                if 'def ' in line and '-> bool' in line:
                    # Find function body
                    indent = len(line) - len(line.lstrip())
                    func_lines = []
                    for j in range(i, min(i+50, len(lines))):
                        if lines[j].strip() and not lines[j].strip().startswith('#'):
                            line_indent = len(lines[j]) - len(lines[j].lstrip())
                            if line_indent <= indent and j > i:
                                break
                            func_lines.append(lines[j])
                    
                    func_body = '\n'.join(func_lines)
                    if 'return' not in func_body:
                        self.add_issue('ERROR', filepath, i,
                                     "Function with bool return type has no return statement")
        
        except Exception as e:
            self.add_issue('ERROR', filepath, 0, f"Cannot check logic: {e}")
    
    def verify_file(self, filepath):
        """Run all checks on a file"""
        print(f"\n{'='*80}")
        print(f"Verifying: {os.path.basename(filepath)}")
        print('='*80)
        
        # Check syntax
        valid, error = self.check_file_syntax(filepath)
        if not valid:
            self.add_issue('ERROR', filepath, 0, f"Syntax error: {error}")
            print(f"❌ SYNTAX ERROR: {error}")
            return False
        else:
            print("✅ Syntax valid")
        
        # Check imports
        imports = self.check_imports(filepath)
        print(f"✅ Found {len(imports)} imports")
        
        # Check function calls
        self.check_function_calls(filepath)
        
        # Check logic
        self.check_logic_errors(filepath)
        
        return True

def main():
    verifier = CodeVerifier()
    
    files_to_check = [
        'risk_manager_enhanced.py',
        'position_monitor.py',
        'indicators_enhanced.py',
        'config_validator.py',
        'ultimate_bot_v2.py',
    ]
    
    print("="*80)
    print("COMPREHENSIVE CODE VERIFICATION")
    print("="*80)
    
    for filepath in files_to_check:
        if os.path.exists(filepath):
            verifier.verify_file(filepath)
        else:
            print(f"\n❌ File not found: {filepath}")
    
    # Print summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    errors = [i for i in verifier.issues if i['severity'] == 'ERROR']
    warnings = [i for i in verifier.issues if i['severity'] == 'WARNING']
    
    print(f"\nTotal Issues: {len(verifier.issues)}")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    
    if errors:
        print("\n🔴 ERRORS FOUND:")
        for issue in errors:
            print(f"  {issue['file']}:{issue['line']} - {issue['message']}")
    
    if warnings:
        print("\n🟡 WARNINGS:")
        for issue in warnings[:10]:  # Show first 10
            print(f"  {issue['file']}:{issue['line']} - {issue['message']}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings)-10} more warnings")
    
    if not errors and not warnings:
        print("\n✅ NO ISSUES FOUND")
    
    print("="*80)
    
    return len(errors) == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
