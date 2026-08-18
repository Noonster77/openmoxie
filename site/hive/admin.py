from django.contrib import admin

from .models import ConversationEvent, PersistentData, SinglePromptChat,MoxieDevice,MoxieSchedule,HiveConfiguration,MentorBehavior,GlobalResponse,TriviaQuestion

admin.site.register(SinglePromptChat)
admin.site.register(MoxieDevice)
admin.site.register(MoxieSchedule)
admin.site.register(HiveConfiguration)
admin.site.register(MentorBehavior)
admin.site.register(GlobalResponse)
admin.site.register(PersistentData)
admin.site.register(ConversationEvent)

@admin.register(TriviaQuestion)
class TriviaQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'enabled')
    list_filter = ('category', 'enabled')
    search_fields = ('question', 'accepted_answers', 'fun_fact')
