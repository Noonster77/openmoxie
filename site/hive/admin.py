from django import forms
from django.contrib import admin, messages

from .models import ConversationEvent, Joke, PersistentData, RobotCommandEvent, SinglePromptChat,MoxieDevice,MoxieSchedule,HiveConfiguration,MentorBehavior,GlobalResponse,TriviaQuestion

class SinglePromptChatAdminForm(forms.ModelForm):
    class Meta:
        model = SinglePromptChat
        fields = '__all__'
        widgets = {
            'max_tokens': forms.NumberInput(attrs={'min': 1, 'max': 8192, 'step': 1}),
            'max_history': forms.NumberInput(attrs={'min': 0, 'max': 200, 'step': 1}),
        }

    def clean_max_tokens(self):
        value = self.cleaned_data['max_tokens']
        if not 1 <= value <= 8192:
            raise forms.ValidationError('Choose a token limit from 1 to 8192.')
        return value

    def clean_max_history(self):
        value = self.cleaned_data['max_history']
        if not 0 <= value <= 200:
            raise forms.ValidationError('Choose a history limit from 0 to 200 messages.')
        return value


@admin.register(SinglePromptChat)
class SinglePromptChatAdmin(admin.ModelAdmin):
    form = SinglePromptChatAdminForm
    list_display = ('name', 'module_id', 'content_id', 'model', 'max_tokens', 'max_history', 'temperature')
    list_editable = ('max_tokens', 'max_history')
    search_fields = ('name', 'module_id', 'content_id', 'model')
    ordering = ('module_id', 'content_id')
    fieldsets = (
        ('Conversation', {'fields': ('name', 'module_id', 'content_id', 'opener', 'prompt')}),
        ('Model and token budget', {
            'fields': ('vendor', 'model', 'max_tokens', 'max_history', 'max_volleys', 'temperature', 'question_probability'),
            'description': 'Leave Model blank to use the model selected in Setup, or enter an exact provider model ID for this conversation. Token and history limits are applied to new sessions immediately after saving.',
        }),
        ('Advanced behavior', {'classes': ('collapse',), 'fields': ('code', 'source_version')}),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from .mqtt.moxie_server import get_instance
        service = get_instance()
        if service:
            service.update_from_database()
            self.message_user(request, 'Conversation settings reloaded into the live service.', messages.SUCCESS)
        else:
            self.message_user(request, 'Conversation saved; the service will load it at startup.', messages.WARNING)
admin.site.register(MoxieDevice)
admin.site.register(MoxieSchedule)
admin.site.register(HiveConfiguration)
admin.site.register(MentorBehavior)
admin.site.register(GlobalResponse)
admin.site.register(PersistentData)
admin.site.register(ConversationEvent)
admin.site.register(Joke)
admin.site.register(RobotCommandEvent)

@admin.register(TriviaQuestion)
class TriviaQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'enabled')
    list_filter = ('category', 'enabled')
    search_fields = ('question', 'accepted_answers', 'fun_fact')
