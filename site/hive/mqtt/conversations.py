'''
CONVERSATIONS - Framework for Moxie remote applications / conversations
'''
import logging
import copy
import random
import re
import traceback
from django.template import Template, Context
from .ai_factory import chat_completion
from ..models import SinglePromptChat
from .volley import Volley

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
        super().__init__(max_history=source.max_history, max_volleys=source.max_volleys, model=source.model, prompt=source.prompt, opener=source.opener, max_tokens=source.max_tokens, temperature=source.temperature)
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


class TriviaChatSession(ChatSession):
    """Deterministic, API-free trivia with a score kept for the current game."""
    QUESTIONS = [
        ("What planet do we live on?", ("earth",)),
        ("How many legs does a spider have?", ("eight", "8")),
        ("What is frozen water called?", ("ice",)),
        ("Which animal says moo?", ("cow",)),
        ("How many days are in a week?", ("seven", "7")),
        ("What is the largest ocean on Earth?", ("pacific",)),
        ("What do caterpillars turn into?", ("butterfly", "butterflies")),
        ("Which shape has three sides?", ("triangle",)),
        ("What gas do people need to breathe?", ("oxygen",)),
        ("What is ten plus five?", ("fifteen", "15")),
    ]

    def __init__(self):
        super().__init__(max_history=0)
        self.reset_game()

    def reset_game(self):
        self._local_data['trivia_index'] = 0
        self._local_data['trivia_score'] = 0

    def handle_volley(self, volley: Volley):
        volley.assign_local_data(self._local_data)
        if volley.request.get('command') == 'prompt':
            self.reset_game()
            text = "Let's play trivia! I'll keep score. " + self.QUESTIONS[0][0]
        else:
            index = self._local_data['trivia_index']
            speech = volley.request.get('speech', '').lower()
            correct = any(re.search(rf'\b{re.escape(answer)}\b', speech) for answer in self.QUESTIONS[index][1])
            if correct:
                self._local_data['trivia_score'] += 1
                result = "Correct!"
            else:
                result = f"Good try! The answer is {self.QUESTIONS[index][1][0]}."
            index += 1
            self._local_data['trivia_index'] = index
            if index >= len(self.QUESTIONS):
                score = self._local_data['trivia_score']
                text = f"{result} You scored {score} out of {len(self.QUESTIONS)}. Great game!"
                volley.set_output(text, None)
                volley.add_launch_or_exit()
                return
            text = f"{result} Your score is {self._local_data['trivia_score']} out of {index}. Next question: {self.QUESTIONS[index][0]}"
        volley.set_output(text, None)
