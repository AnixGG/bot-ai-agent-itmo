def parser_question(q: str):
    split_q = q.split("\n")
    question = []
    var_answers = []
    idx_q = 0
    for idx_q, part_q in enumerate(split_q):
        question.append(part_q)
        if part_q[-1] == "?":
            break
    curr_num_var = 1
    for idx in range(idx_q+1, len(split_q)):
        part_q = split_q[idx]
        if str(curr_num_var) == part_q[0]:
            var_answers.append(part_q)
            curr_num_var += 1
        else:
            var_answers[-1] = var_answers[-1] + " " + part_q
    return ' '.join(question), var_answers


def parser_response(response):
    return response["result"]["alternatives"][0]["message"]["text"]


def decrease(q):
    if len(q) > 8192:
        return q[:8192]
    return q

