from enum import Enum
from django.db import models
from django.core.validators import validate_comma_separated_integer_list
from django.core.exceptions import ValidationError

class AIVendor(Enum):
    OPEN_AI = 1

class SinglePromptChat(models.Model):
    name = models.CharField(max_length=200)
    module_id = models.CharField(max_length=200)
    content_id = models.CharField(max_length=200)
    max_history = models.IntegerField(default=20)
    max_volleys = models.IntegerField(default=9999)
    opener = models.TextField()
    prompt = models.TextField()
    vendor = models.IntegerField(choices=[(tag.value, tag.name) for tag in AIVendor],default=AIVendor.OPEN_AI.value)
    model = models.CharField(max_length=200, default="gpt-4o-mini")
    max_tokens = models.IntegerField(default=70)
    temperature = models.FloatField(default=0.5)
    question_probability = models.FloatField(default=0.35)
    code = models.TextField(null=True, blank=True) # Python code for filter methods
    source_version = models.IntegerField(default=1)
    
    def __str__(self):
        return self.name
    
class MoxieSchedule(models.Model):
    name = models.CharField(max_length=200)
    schedule = models.JSONField()
    source_version = models.IntegerField(default=1)
    
    def __str__(self):
        return self.name

class DevicePermit(Enum):
    UNKNOWN = 1
    PENDING = 2
    ALLOWED = 3

class MoxieDevice(models.Model):
    device_id = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    permit = models.IntegerField(choices=[(tag.value, tag.name) for tag in DevicePermit],default=DevicePermit.UNKNOWN.value)
    schedule = models.ForeignKey(MoxieSchedule, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    last_connect = models.DateTimeField(null=True, blank=True)
    last_disconnect = models.DateTimeField(null=True, blank=True)
    state = models.JSONField(null=True, blank=True)
    state_updated = models.DateTimeField(null=True, blank=True)
    robot_config = models.JSONField(null=True, blank=True)
    robot_settings = models.JSONField(null=True, blank=True)
    conversation_profile = models.TextField(default=(
        "You are Moxie, a warm, playful, age-appropriate robot friend. Keep replies short and "
        "conversational, ask at most one question at a time, and encourage the child to talk to "
        "a trusted adult about safety, health, or anything that worries them."
    ))
    conversation_memory_enabled = models.BooleanField(default=True)
    speaker_names = models.JSONField(default=list, blank=True)
    trivia_categories = models.JSONField(default=list, blank=True)
    trivia_question_count = models.PositiveSmallIntegerField(default=10)
    trivia_seen_question_ids = models.JSONField(default=list, blank=True)

    def is_paired(self):
        if self.robot_config:
            return not (self.robot_config.get('pairing_status') == 'unpairing')
        return True

    def __str__(self):
        return self.name if self.name else self.device_id

class MoxieLogs(models.Model):
    device = models.ForeignKey(MoxieDevice, on_delete=models.CASCADE)
    timestamp = models.TimeField()
    uid = models.IntegerField()
    tag = models.CharField(max_length=80)
    message = models.TextField()

class HiveConfiguration(models.Model):
    name = models.CharField(max_length=200)
    openai_api_key = models.TextField(null=True, blank=True, default='')
    external_host = models.CharField(max_length=255, null=True, blank=True, default='')
    allow_unverified_bots = models.BooleanField(default=False)
    google_api_key = models.TextField(null=True, blank=True, default='')
    common_config = models.JSONField(null=True, blank=True)
    common_settings = models.JSONField(null=True, blank=True)
    chat_provider = models.CharField(max_length=20, default='openai')
    chat_base_url = models.CharField(max_length=500, blank=True, default='http://host.docker.internal:1234/v1')
    chat_model = models.CharField(max_length=255, default='gpt-4o-mini')
    stt_provider = models.CharField(max_length=20, default='openai')
    local_stt_model = models.CharField(max_length=100, default='small.en')

    def __str__(self):
        return self.name

class MentorBehavior(models.Model):
    device = models.ForeignKey(MoxieDevice, on_delete=models.CASCADE)
    # Fields for MBH
    module_id = models.CharField(max_length=80, null=True, blank=True)
    content_id = models.CharField(max_length=80, null=True, blank=True)
    content_day = models.CharField(max_length=80, null=True, blank=True)
    timestamp = models.BigIntegerField()
    action = models.CharField(max_length=80, null=True, blank=True)
    instance_id = models.BigIntegerField()
    ended_reason = models.CharField(max_length=80, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['device', 'timestamp'], name='device_timestamp_idx'),
        ]

    def __str__(self):
        return f'{self.timestamp}-{self.device}-{self.module_id}/{self.content_id}-{self.action}'


class GlobalAction(Enum):
    RESPONSE = 1
    LAUNCH = 2
    CONFIRM_LAUNCH = 3
    METHOD = 4
    SLEEP = 5
    EXIT = 6

class GlobalResponse(models.Model):
    name = models.TextField()      # common name
    pattern = models.TextField()   # regex pattern to match speech
    entity_groups = models.CharField(max_length=255, validators=[validate_comma_separated_integer_list], null=True, blank=True)
    action = models.IntegerField(choices=[(tag.value, tag.name) for tag in GlobalAction],default=GlobalAction.RESPONSE.value)
    response_text = models.TextField(null=True, blank=True)  # plaintext response
    response_markup = models.TextField(null=True, blank=True)  # markup override response
    module_id = models.CharField(max_length=80, null=True, blank=True)  # for launches, module ID to target
    content_id = models.CharField(max_length=80, null=True, blank=True) # for launches, content ID to target
    code = models.TextField(null=True, blank=True) # Python code for METHOD, w/ def get_response(request, response, entities):
    sort_key = models.IntegerField(default=1) # in case ordering matters, they order desc so high goes first
    source_version = models.IntegerField(default=1)

    # Ensure we have all we need
    def clean(self):
        if self.action == GlobalAction.METHOD.value and not self.code:
            raise ValidationError({'code': 'Code is required for METHOD action'})
        elif (self.action == GlobalAction.LAUNCH.value or self.action == GlobalAction.CONFIRM_LAUNCH.value) and not self.module_id:
            raise ValidationError({'module_id': 'Module ID is required for LAUNCH actions'})
        elif self.action != GlobalAction.METHOD.value and not self.response_text:
            raise ValidationError({'response_text': 'Response Text is required for actions except METHOD'})
        
    def __str__(self):
        return self.name
    
class PersistentData(models.Model):
    device = models.OneToOneField(MoxieDevice, on_delete=models.CASCADE)
    data = models.JSONField()

    def __str__(self):
        return f'{self.device} - Data'


class ConversationEvent(models.Model):
    device = models.ForeignKey(MoxieDevice, on_delete=models.CASCADE, related_name='conversation_events')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    role = models.CharField(max_length=20)
    text = models.TextField()
    module_id = models.CharField(max_length=100, blank=True, default='')
    content_id = models.CharField(max_length=100, blank=True, default='')
    safety_flagged = models.BooleanField(default=False, db_index=True)
    safety_categories = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['device', 'created_at'], name='conversation_device_time')]

    def __str__(self):
        return f'{self.created_at} {self.device} {self.role}: {self.text[:60]}'


class TriviaQuestion(models.Model):
    category = models.CharField(max_length=60, db_index=True)
    question = models.TextField()
    accepted_answers = models.JSONField(default=list)
    fun_fact = models.TextField(blank=True, default='')
    enabled = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['category', 'question']

    def __str__(self):
        return f'{self.category}: {self.question}'


class Joke(models.Model):
    collection = models.CharField(max_length=60, default='Family favorites', db_index=True)
    setup = models.TextField()
    punchline = models.TextField()
    enabled = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['collection', 'setup']

    def __str__(self):
        return f'{self.collection}: {self.setup}'


class RobotCommandEvent(models.Model):
    device = models.ForeignKey(MoxieDevice, on_delete=models.CASCADE, related_name='command_events')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    action = models.CharField(max_length=40)
    label = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=20, default='sent')
    detail = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.device} {self.action} {self.status}'
