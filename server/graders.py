# graders.py

def _base_grade(action, task, found_bug):
    """Base grading logic shared across tasks."""
    reward = 0.0
    done = False
    status = ""
    new_found_bug = found_bug

    if action.command == "list_files":
        status = f"Files in PR: {', '.join(task['files'].keys())}"
        
    elif action.command == "view_file":
        if action.file_path in task['files']:
            status = f"Viewing {action.file_path}"
            reward += 0.05  # Tiny reward for exploring
        else:
            status = "File not found."
            reward -= 0.05
            
    elif action.command == "add_comment":
        if action.file_path in task['files']:
            status = f"Comment added to {action.file_path} on line {action.line_number}."
            # Check if they found the exact bug
            if (not found_bug and 
                action.file_path == task['bug_file'] and 
                action.line_number == task['bug_line']):
                new_found_bug = True
                reward += 0.3  # Partial credit for finding the issue
                status += " [Grader: Bug identified!]"
        else:
            status = "Invalid file for comment."
            reward -= 0.05
            
    elif action.command == "submit_review":
        done = True
        decision = action.text.lower().strip()
        
        if decision == "request_changes" and not task['should_approve']:
            if found_bug:
                reward += 0.7  # Perfect completion
                status = "PR properly rejected with correct bugs found. Task Complete!"
            else:
                reward += 0.2  # Rejected, but missed the actual specific bug
                status = "PR rejected, but exact bug line was not commented on."
        elif decision == "approve" and task['should_approve']:
            reward += 1.0
            status = "PR correctly approved. Task Complete!"
        else:
            reward -= 0.5  # Heavy penalty for approving bad code
            status = "Critical Failure: Approved vulnerable/broken code or rejected good code."
    else:
        status = "Unknown command."
        reward -= 0.05

    return reward, done, status, new_found_bug

def grade_easy(action, task, found_bug):
    # You can customize easy-level specific scoring here in the future
    return _base_grade(action, task, found_bug)

def grade_medium(action, task, found_bug):
    # You can customize medium-level specific scoring here in the future
    return _base_grade(action, task, found_bug)

def grade_hard(action, task, found_bug):
    # You can customize hard-level specific scoring here in the future
    return _base_grade(action, task, found_bug)

def grade_expert(action, task, found_bug):
    # You can customize expert-level specific scoring here in the future
    return _base_grade(action, task, found_bug)