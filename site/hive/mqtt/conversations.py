'''
CONVERSATIONS - Framework for Moxie remote applications / conversations
'''
import logging
import ast
import copy
import random
import re
import traceback
from django.template import Template, Context
from .ai_factory import chat_completion
from ..models import Joke, MoxieDevice, SinglePromptChat, TriviaQuestion
from .volley import Volley
from .conversation_log import safety_redirect

logger = logging.getLogger(__name__)

_DEFAULT_SUMMARY_PROMPT = "Summarize the following conversation between the friendly robot Moxie, and the user.  Keep the summary brief, but include any important details."

'''
Base type of a module that has a chat session interaction on Moxie.  It
manages the history, rotating out records to keep tokens more lean.
'''
class ChatSession:
    def __init__(self, max_history=20):
        self._history = []
        self._max_history = max_history
        self._total_volleys = 0
        self._local_data = {}

    def add_history(self, role, message, history=None):
        if history is None:
            history = self._history
            self._total_volleys += 1
        if history and history[-1].get("role") == role:
            # same role, append text
            history[-1]["content"] =  history[-1].get("content", '') + ' ' + message
        else:
            history.append({ "role": role, "content": message })
            if len(history) > self._max_history:
                del history[:-self._max_history]

    def is_empty(self):
        return len(self._history) == 0
    
    @property
    def total_volleys(self):
        return self._total_volleys
    
    def reset(self):
        self._history = []
        self._total_volleys = 0
        
    @property
    def local_data(self):
        return self._local_data
    
    def get_opener(self, msg='Welcome to open chat'):
        return msg,self.overflow()

    def ingest_notify(self, volley:Volley):
        rcr = volley.request
        # RULES - speech field is what 'assistant' said, but we should skip the [animation]
        # 'user' speech comes from extra_lines[].text when .context_type=='input'
        for line in rcr.get('extra_lines', []):
            if line['context_type'] == 'input':
                self.add_history('user', line['text'])
        speech = rcr.get('speech')
        if speech and 'animation:' not in speech and 'silent:' not in speech:
            self.add_history('assistant', speech)

    def next_response(self, speech, context):
        logger.debug(f'Inference using history:\n{self._history}')
        return f"chat history {len(self._history)}", None

    def overflow(self):
        return False
    
    def handle_volley(self, volley:Volley):
        pass

    def summarize(self, model=None, prompt_base=None, max_tokens=None):
        return "No summary available."

    def has_complete_hook(self):
        return False
    
    def complete_hook(self, device_id, volley:Volley):
        pass

'''
Our simple Single Prompt conversation.  It uses the ChatSession to manage the history
of the conversation and focuses on keeping the conversation within volley limits and
make inferences to OpenAI.
'''
class SingleContextChatSession(ChatSession):
    def __init__(self, 
                 max_history=20, 
                 max_volleys=9999,
                 prompt="You are a having a conversation with your friend. Make it interesting and keep the conversation moving forward. Your utterances are around 30-40 words long. Ask only one question per response and ask it at the end of your response.",
                 opener="Hi there!  Welcome to Open Moxie chat!",
                 model="gpt-3.5-turbo",
                 max_tokens=70,
                 temperature=0.5,
                 question_probability=0.35,
                 exit_line="Well, that was fun.  Let's move on."
                 ):
        super().__init__(max_history)
        self._max_volleys = max_volleys        
        self._context = [ { "role": "system", 
            "content": prompt
            } ]
        self._opener = opener
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._question_probability = max(0.0, min(1.0, question_probability))
        self._exit_line = exit_line
        self._auto_history = False
        self._pre_filter = None
        self._post_filter = None
        self._notify_handler = None
        self._complete_handler = None
        self._prompt_template = Template(prompt)

    def set_filters(self, pre_filter=None, post_filter=None, complete_handler=None, notify_handler=None):
        self._pre_filter = pre_filter
        self._post_filter = post_filter
        self._complete_handler = complete_handler
        self._notify_handler = notify_handler

    # For web-based, we have no Moxie and no Notify channel, so auto-history is used
    def set_auto_history(self, val):
        self._auto_history = val
    
    # Check if we exceed max volleys for a conversation
    def overflow(self):
        return self._total_volleys >= self._max_volleys
    
    # Render an updated prompt context for this volley
    def make_volley_context(self, volley:Volley):
        ctx = self._prompt_template.render(Context({'volley': volley, 'session': self}))
        ctx += "\n\nYour response will be spoken aloud by Moxie. Do not use emoji, markdown, lists, or stage directions. Finish every sentence."
        ctx += "\nUse profile details sparingly. Do not repeatedly mention pets, relatives, hobbies, or the person's name. Vary topics naturally and follow what the person actually says."
        current_speech = volley.request.get('speech', '').lower()
        if not any(word in current_speech for word in ('dog', 'dogs', 'hazel', 'stella', 'pet', 'pets')):
            ctx += "\nDo not mention dogs, pets, Hazel, or Stella in this response. The current speaker did not bring them up."
        active_speaker = volley.persist_data.get('active_speaker')
        if active_speaker:
            ctx += f"\nThe person currently speaking identified themself as {active_speaker}."
        if self._question_probability <= 0:
            ctx += "\nDo not ask the person any questions. Give an answer, not a quiz, follow-up prompt, or offer to do more."
        elif random.random() < self._question_probability:
            ctx += "\nEnd this response with one short, friendly question related to the conversation."
        else:
            ctx += "\nDo not force a question into this response."
        if volley.conversation_profile:
            ctx += "\n\nCHILD PROFILE AND CONVERSATION RULES:\n" + volley.conversation_profile
        if volley.conversation_memory_enabled:
            remembered = volley.persist_data.get('conversation_memory', {}).get('recent', [])
            if remembered:
                memory_lines = [f"{item.get('role', 'user')}: {item.get('content', '')}" for item in remembered[-20:]]
                ctx += "\n\nRECENT CONVERSATION MEMORY (use naturally; do not claim perfect memory):\n" + "\n".join(memory_lines)
        return [ { "role": "system", 
                    "content": ctx
                    } ]

    def remember_exchange(self, volley, speech, response):
        if not volley.conversation_memory_enabled:
            return
        recent = volley.persist_data.setdefault('conversation_memory', {}).setdefault('recent', [])
        recent.extend([
            {'role': 'user', 'content': speech},
            {'role': 'assistant', 'content': response},
        ])
        del recent[:-20]
    
    # Handle Moxie saying something, accumulate to history
    def ingest_notify(self, volley:Volley):
        super().ingest_notify(volley)
        if self._notify_handler:
            self._notify_handler(volley, self)

    # Handle a volley, using its request and populating the response
    def handle_volley(self, volley:Volley):
        volley.assign_local_data(self._local_data)
        try:
            cmd = volley.request.get('command')
            # when prompting into a convo, make sure its clean
            if cmd == "prompt" and not self.is_empty():
                self.reset()
            # preprocess, if filter returns True, we are done
            if self._pre_filter:
                logger.debug("Running volley pre-filter")
                if self._pre_filter(volley, self):
                    # handle any actions tags in the response
                    volley.ingest_action_tags()
                    return
            
            # Handle prompt vs next response
            if cmd == "prompt" or (cmd == "reprompt" and self.is_empty()):
                text,overflow = self.get_opener()
            else:
                speech = "hm" if volley.request.get("command")=="reprompt" else volley.request["speech"]
                redirect_text = safety_redirect(speech)
                if redirect_text:
                    text, overflow = redirect_text, False
                else:
                    text,overflow = self.next_response(speech, self.make_volley_context(volley))
                self.remember_exchange(volley, speech, text)
            volley.set_output(text, None)
            if overflow:
                volley.add_launch_or_exit()
            # postprocess the volley
            if self._post_filter:
                logger.debug("Running volley post-filter")
                self._post_filter(volley, self)
            # handle any actions tags in the response
            volley.ingest_action_tags()
        except Exception as e:
            stack = traceback.format_exc()
            logger.error(f"Error handling volley: {e}\n{stack}")
            err_text = f"Error handling volley: {e}"
            volley.create_response() # flush any pre-exception response changes
            volley.set_output(err_text,err_text)

    # Get the next thing we should say, given the user speech and the history
    def next_response(self, speech, context):
        of = self.overflow()
        if self._auto_history:
            # accumulating automatically, no interruptions or aborts
            self.add_history('user', speech)
            history = self._history
        else:
            # clone, add new input, official history comes from notify
            history = copy.deepcopy(self._history)
            self.add_history('user', speech, history)
        try:
            resp = chat_completion(
                context + history,
                fallback_model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
        except Exception as e:
            logger.warning(f'Exception attempting inference: {e}')
            resp = "Oh no.  I have run into a bug"
        if of:
            resp += " " + self._exit_line
        if self._auto_history:
            self.add_history('assistant', resp)
        return resp, of
    
    # Prompt in this case is an opener line to say when we start the conversation module
    def get_opener(self):
        # Supports multiple random prompts separated by |, pick a random one
        opener = random.choice(self._opener.split('|'))
        resp,overflow = super().get_opener(msg=opener)
        if self._auto_history:
            self.add_history('assistant', resp)
        return resp,overflow
    
    def summarize(self, model=None, prompt_base=None, max_tokens=None, append_transcript=True):
        try:
            if not model:
                model = self._model
            if not max_tokens:
                max_tokens = self._max_tokens
            prompt = prompt_base if prompt_base else _DEFAULT_SUMMARY_PROMPT
            if append_transcript:
                # Concatenate the chat history into a single string
                chat_transcript = "\n".join([f"{'Moxie' if msg['role'] == 'assistant' else msg['role']}: {msg['content']}" for msg in self._history])
                prompt += f"\nTranscript:\n\n{chat_transcript}"
            # Summarize the chat transcript
            msgs = [ { "role": "user", 
                "content": prompt
                } ]
            resp = chat_completion(
                msgs,
                fallback_model=model,
                max_tokens=max_tokens,
                temperature=self._temperature,
            )
            return resp
        except Exception as e:
            stack = traceback.format_exc()
            logger.error(f"Error summarizing chat: {e}\n{stack}")
            return f"Error summarizing chat: {e}."


    def has_complete_hook(self):
        return self._complete_handler is not None
    
    def complete_hook(self, volley:Volley):
        try:
            self._complete_handler(volley, self)
        except Exception as e:
            stack = traceback.format_exc()
            logger.error(f"Error running complete hook: {e}\n{stack}")

# A database backed version, the way we normally load them
class SinglePromptDBChatSession(SingleContextChatSession):
    def __init__(self, pk):
        source = SinglePromptChat.objects.get(pk=pk)
        super().__init__(max_history=source.max_history, max_volleys=source.max_volleys, model=source.model, prompt=source.prompt, opener=source.opener, max_tokens=source.max_tokens, temperature=source.temperature, question_probability=source.question_probability)
        if source.code:
            try:
                loc = locals()
                exec(source.code, globals(), loc)
                self.set_filters(pre_filter=loc.get('pre_process'), 
                                 post_filter=loc.get('post_process'),
                                 complete_handler=loc.get('complete_handler'),
                                 notify_handler=loc.get('notify_handler'))
            except Exception as e:
                logger.error(f"Error loading code for chat session: {e}")


class HomeworkChatSession(SinglePromptDBChatSession):
    """Answer-first homework help with a zero-latency path for basic arithmetic."""

    _UNITS = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
        'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
        'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
        'fourteen': 14, 'fifteen': 15, 'sixteen': 16,
        'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
    }
    _TENS = {
        'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
        'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
    }
    _BINARY_OPERATORS = {
        ast.Add: lambda left, right: left + right,
        ast.Sub: lambda left, right: left - right,
        ast.Mult: lambda left, right: left * right,
        ast.Div: lambda left, right: left / right,
        ast.Mod: lambda left, right: left % right,
        ast.Pow: lambda left, right: left ** right,
    }

    def __init__(self, pk):
        super().__init__(pk)
        self._max_tokens = min(self._max_tokens, 45)
        self._temperature = 0.1
        self._question_probability = 0.0

    @classmethod
    def _words_to_number(cls, text):
        words = [word for word in text.strip().replace('-', ' ').split() if word != 'and']
        if not words:
            return None
        if all(re.fullmatch(r'\d+(?:\.\d+)?', word) for word in words):
            return ''.join(words)
        if 'point' in words:
            point = words.index('point')
            whole = cls._words_to_number(' '.join(words[:point])) or '0'
            decimals = [str(cls._UNITS[word]) for word in words[point + 1:] if word in cls._UNITS and cls._UNITS[word] < 10]
            if len(decimals) != len(words[point + 1:]) or not decimals:
                return None
            return f'{whole}.{"".join(decimals)}'
        total = current = 0
        for word in words:
            if word in cls._UNITS:
                current += cls._UNITS[word]
            elif word in cls._TENS:
                current += cls._TENS[word]
            elif word == 'hundred':
                current = (current or 1) * 100
            elif word == 'thousand':
                total += (current or 1) * 1000
                current = 0
            else:
                return None
        return str(total + current)

    @classmethod
    def _normalize_expression(cls, speech):
        expression = speech.lower().strip().replace(',', '').replace('×', '*').replace('÷', '/')
        expression = re.sub(r'^(?:moxie[, ]+)?(?:what(?: is|\'s)|calculate|compute|solve|the answer to)\s+', '', expression)
        replacements = (
            (r'raised to the power of|to the power of', '**'),
            (r'multiplied by', '*'), (r'divided by', '/'),
            (r'plus', '+'), (r'minus', '-'), (r'times', '*'),
        )
        for pattern, replacement in replacements:
            expression = re.sub(rf'\b(?:{pattern})\b', replacement, expression)
        expression = expression.rstrip(' ?.=')
        parts = re.split(r'(\*\*|[+\-*/()%])', expression)
        normalized = []
        for part in parts:
            if not part or re.fullmatch(r'\s*(?:\*\*|[+\-*/()%])\s*', part):
                normalized.append(part.strip())
                continue
            number = cls._words_to_number(part)
            if number is None:
                return None
            normalized.append(number)
        result = ''.join(normalized)
        return result if re.search(r'[+\-*/%]', result) else None

    @classmethod
    def _evaluate_expression(cls, node):
        if isinstance(node, ast.Expression):
            return cls._evaluate_expression(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = cls._evaluate_expression(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and type(node.op) in cls._BINARY_OPERATORS:
            left = cls._evaluate_expression(node.left)
            right = cls._evaluate_expression(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError('Exponent is too large')
            value = cls._BINARY_OPERATORS[type(node.op)](left, right)
            if abs(value) > 1e15:
                raise ValueError('Result is too large')
            return value
        raise ValueError('Unsupported arithmetic expression')

    @classmethod
    def solve_arithmetic(cls, speech):
        expression = cls._normalize_expression(speech)
        if not expression:
            return None
        try:
            value = cls._evaluate_expression(ast.parse(expression, mode='eval'))
        except ZeroDivisionError:
            return 'That is undefined because division by zero is not allowed.'
        except (SyntaxError, TypeError, ValueError, OverflowError):
            return None
        if isinstance(value, float):
            value = round(value, 8)
            rendered = str(int(value)) if value.is_integer() else f'{value:.8f}'.rstrip('0').rstrip('.')
        else:
            rendered = str(value)
        return f'{rendered}.'

    @staticmethod
    def concise_answer(text):
        sentences = re.split(r'(?<=[.!?])\s+|\n+', (text or '').strip())
        answer = []
        for sentence in sentences:
            lowered = sentence.lower().strip()
            if not sentence or '?' in sentence:
                continue
            if re.match(r'^(?:would you|do you|can i|shall i|let me know|i can also|feel free|ask me)', lowered):
                continue
            answer.append(sentence)
            if len(answer) == 2:
                break
        concise = ' '.join(answer) or "I don't have a reliable answer."
        words = concise.split()
        if len(words) > 45:
            concise = ' '.join(words[:45]).rstrip(',:;-') + '.'
        return concise.replace('?', '.')

    def next_response(self, speech, context):
        arithmetic = self.solve_arithmetic(speech)
        if arithmetic is not None:
            return arithmetic, self.overflow()
        response, overflow = super().next_response(speech, context)
        return self.concise_answer(response), overflow


class TriviaChatSession(ChatSession):
    """Configurable, API-free trivia with category filters and spoken-friendly pacing."""
    FALLBACK_QUESTIONS = [
        {'category': 'Science', 'question': 'What planet do we live on?', 'answers': ['earth'], 'fun_fact': ''},
        {'category': 'Animals', 'question': 'How many legs does a spider have?', 'answers': ['eight', '8'], 'fun_fact': 'Spiders use tiny hairs on their legs to sense vibrations.'},
        {'category': 'Math', 'question': 'What is ten plus five?', 'answers': ['fifteen', '15'], 'fun_fact': ''},
    ]
    PATTER = [
        'Tiny drumroll for the next one.',
        'My imaginary quiz buzzer is ready.',
        'Okay, brain gears: spin, spin, spin.',
        'Next one coming in hot. Well, robot-temperature hot.',
        'Excellent effort. The scoreboard is wearing a fancy hat.',
        'Let us hop to another question. Boing.',
        'Here comes a fresh mystery for your noodle.',
    ]

    def __init__(self):
        super().__init__(max_history=0)
        self.reset_game()

    def reset_game(self, device_id=None):
        self._local_data['trivia_index'] = 0
        self._local_data['trivia_score'] = 0
        self._local_data['last_patter'] = ''
        questions = []
        count = 10
        try:
            device = MoxieDevice.objects.filter(device_id=device_id).first() if device_id else None
            categories = device.trivia_categories if device else []
            count = max(3, min(20, device.trivia_question_count if device else 10))
            query = TriviaQuestion.objects.filter(enabled=True)
            if categories:
                query = query.filter(category__in=categories)
            rows = list(query)
            unseen_rows = rows
            rolled_deck = False
            if device:
                seen = {int(pk) for pk in device.trivia_seen_question_ids}
                unseen_rows = [row for row in rows if row.pk not in seen]
                requested = min(count, len(rows))
                # Finish the old deck, then refill from a new shuffled deck without
                # duplicating a question inside this game.
                if len(unseen_rows) < requested:
                    rolled_deck = True
                    random.shuffle(unseen_rows)
                    unseen_ids = {row.pk for row in unseen_rows}
                    refill = [row for row in rows if row.pk not in unseen_ids]
                    random.shuffle(refill)
                    unseen_rows += refill[:requested - len(unseen_rows)]
            questions = [
                {'id': row.pk, 'category': row.category, 'question': row.question,
                 'answers': [str(answer).lower() for answer in row.accepted_answers], 'fun_fact': row.fun_fact}
                for row in unseen_rows
            ]
        except Exception:
            logger.exception('Could not load configured trivia; using built-in fallback')
        if not questions:
            questions = copy.deepcopy(self.FALLBACK_QUESTIONS)
        random.shuffle(questions)
        self._local_data['trivia_questions'] = questions[:min(count, len(questions))]
        if device and questions and questions[0].get('id'):
            selected_ids = [item['id'] for item in self._local_data['trivia_questions']]
            device.trivia_seen_question_ids = selected_ids if rolled_deck else list(dict.fromkeys(device.trivia_seen_question_ids + selected_ids))
            device.save(update_fields=['trivia_seen_question_ids'])

    def _patter(self):
        choices = [line for line in self.PATTER if line != self._local_data.get('last_patter')]
        line = random.choice(choices)
        self._local_data['last_patter'] = line
        return line

    def _ask(self, index):
        item = self._local_data['trivia_questions'][index]
        return f"Question {index + 1}, from {item['category']}. {item['question']}"

    def handle_volley(self, volley: Volley):
        volley.assign_local_data(self._local_data)
        if volley.request.get('command') == 'prompt':
            self.reset_game(volley.device_id)
            total = len(self._local_data['trivia_questions'])
            text = f"Let's play {total} questions of mixed-up trivia. I'll keep score. {self._ask(0)}"
        elif volley.request.get('command') == 'reprompt':
            text = "No problem. Here it is again. " + self._ask(self._local_data['trivia_index'])
        else:
            index = self._local_data['trivia_index']
            questions = self._local_data['trivia_questions']
            if index >= len(questions):
                self.reset_game(volley.device_id)
                index = 0
                questions = self._local_data['trivia_questions']
            speech = volley.request.get('speech', '').lower()
            item = questions[index]
            correct = any(re.search(rf'\b{re.escape(answer)}\b', speech) for answer in item['answers'])
            if correct:
                self._local_data['trivia_score'] += 1
                result = random.choice(['Correct!', 'You got it!', 'That is exactly right!', 'Yes! Nice thinking!'])
            else:
                result = f"Good try. The answer is {item['answers'][0]}."
            if item.get('fun_fact'):
                result += ' ' + item['fun_fact']
            index += 1
            self._local_data['trivia_index'] = index
            if index >= len(questions):
                score = self._local_data['trivia_score']
                text = f"{result} Final score: {score} out of {len(questions)}. Great game! My quiz circuits are impressed."
                volley.set_output(text, None)
                volley.add_launch_or_exit()
                return
            score_line = f" Your score is {self._local_data['trivia_score']} out of {index}." if index % 3 == 0 else ''
            text = f"{result}{score_line} {self._patter()} {self._ask(index)}"
        volley.set_output(text, None)


class JokeChatSession(ChatSession):
    """API-free family joke player with collection filters and no repeats per run."""
    def __init__(self):
        super().__init__(max_history=0)
        self._local_data['jokes'] = []
        self._local_data['joke_index'] = 0

    def _load(self, device_id):
        device = MoxieDevice.objects.filter(device_id=device_id).first()
        selected = (device.robot_config or {}).get('joke_collections', []) if device else []
        query = Joke.objects.filter(enabled=True)
        if selected:
            query = query.filter(collection__in=selected)
        jokes = list(query.values('setup', 'punchline', 'collection'))
        random.shuffle(jokes)
        self._local_data['jokes'] = jokes
        self._local_data['joke_index'] = 0

    def handle_volley(self, volley: Volley):
        volley.assign_local_data(self._local_data)
        if volley.request.get('command') == 'prompt' or not self._local_data['jokes']:
            self._load(volley.device_id)
        jokes = self._local_data['jokes']
        if not jokes:
            volley.set_output("I don't have any enabled jokes yet. Ask a grown-up to add one in Parent Corner.", None)
            volley.add_launch_or_exit()
            return
        index = self._local_data['joke_index']
        if volley.request.get('command') == 'prompt':
            text = f"Joke time! {jokes[index]['setup']}"
        else:
            current = jokes[index]
            index += 1
            if index >= len(jokes):
                text = f"{current['punchline']} That's every joke in this mix. Thanks for laughing with me!"
                volley.set_output(text, None)
                volley.add_launch_or_exit()
                return
            self._local_data['joke_index'] = index
            text = f"{current['punchline']} Here's another. {jokes[index]['setup']}"
        volley.set_output(text, None)
