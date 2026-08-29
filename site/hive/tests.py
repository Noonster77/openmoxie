import json
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.conf import settings

from .models import ConversationEvent, GlobalResponse, HiveConfiguration, Joke, MoxieDevice, MoxieSchedule, RobotCommandEvent, SinglePromptChat, TriviaQuestion
from .mqtt.moxie_server import MoxieServer
from .mqtt.moxie_remote_chat import RemoteChat
from .mqtt.robot_data import RobotData
from .mqtt.conversations import ChatSession, HomeworkChatSession, JokeChatSession, SingleContextChatSession, TriviaChatSession
from .mqtt.volley import Volley
from .mqtt.conversation_log import record_conversation, safety_redirect
from .mqtt.global_responses import GlobalResponses
from .mqtt.scheduler import expand_schedule
from .mqtt import ai_factory


class MQTTServiceTests(SimpleTestCase):
    def test_sqlite_is_configured_for_bounded_concurrent_writes(self):
        options = settings.DATABASES['default']['OPTIONS']

        self.assertEqual(options['timeout'], 10)
        self.assertEqual(options['transaction_mode'], 'IMMEDIATE')

    def test_connect_is_async_and_starts_retry_loop(self):
        server = MoxieServer.__new__(MoxieServer)
        server._robot = SimpleNamespace(create_jwt=lambda project: "token")
        server._mqtt_project_id = "openmoxie"
        server._mqtt_endpoint = "mqtt"
        server._port = 8883
        server._client = MagicMock()

        server.connect(start=True)

        server._client.connect_async.assert_called_once_with("mqtt", 8883, 60)
        server._client.reconnect_delay_set.assert_called_once_with(min_delay=1, max_delay=30)
        server._client.loop_start.assert_called_once()

    def test_device_state_topic_is_parsed_without_confusing_sys_topics(self):
        server = MoxieServer.__new__(MoxieServer)
        server._status_lock = threading.Lock()
        server._status = {}
        server.on_device_state = MagicMock()
        server.on_device_event = MagicMock()
        server.on_client_metrics = MagicMock()
        server.on_sys_log_message = MagicMock()
        message = SimpleNamespace(
            topic="/devices/d_abc123/state",
            payload=json.dumps({"battery_level": 50}).encode(),
        )

        server.on_message(None, None, message)

        server.on_device_state.assert_called_once_with("d_abc123", message)
        self.assertEqual(server._status["last_device_id"], "d_abc123")

    def test_background_errors_are_exposed_in_service_status(self):
        server = MoxieServer.__new__(MoxieServer)
        server._status_lock = threading.Lock()
        server._status = {"last_processing_error": None}
        server._worker_queue = ThreadPoolExecutor(max_workers=1)

        def broken_task():
            raise ValueError("bad robot state")

        future = server._submit_worker(broken_task)
        with self.assertRaises(ValueError):
            future.result(timeout=2)
        server._worker_queue.shutdown()

        self.assertIn("bad robot state", server._status["last_processing_error"])

    @patch("hive.mqtt.moxie_server.logger.debug")
    def test_empty_battery_state_error_log_is_ignored(self, debug):
        server = MoxieServer.__new__(MoxieServer)
        server.check_device_connect = MagicMock(return_value=None)
        message = SimpleNamespace(payload=json.dumps({
            "tag": "Unity", "message": "[BSTATE_ERROR] [LizardErrorEvent]",
        }).encode())

        server.on_device_event("d_battery", "device-logs", message)

        debug.assert_not_called()

    @patch("hive.views.get_instance", return_value=None)
    def test_connection_status_reports_supervisor_not_started(self, get_instance):
        response = self.client.get(reverse("hive:connection_status"))

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["broker_connected"])


class RobotStateTests(TestCase):
    def test_first_partial_state_does_not_crash_when_previous_state_is_null(self):
        device = MoxieDevice.objects.create(device_id="d_first_state")
        robot_data = RobotData.__new__(RobotData)

        robot_data.update_state_atomic(device.device_id, {"awake": True})

        device.refresh_from_db()
        self.assertEqual(device.state, {"awake": True})

    def test_connected_details_include_live_mode(self):
        robot_data = RobotData.__new__(RobotData)
        robot_data._robot_map = {
            "d_live": {
                "state": {"mode": "sleep"},
                "state_received_at": "2026-08-17T18:00:00+00:00",
            }
        }

        self.assertEqual(robot_data.connected_details()["d_live"]["mode"], "sleep")

    def test_idle_does_not_prematurely_confirm_wake_transition(self):
        device = MoxieDevice.objects.create(device_id='d_transition')
        command = RobotCommandEvent.objects.create(
            device=device, action='wake', label='Wake & Chat', status='sent',
        )
        server = MoxieServer.__new__(MoxieServer)
        server._robot_data = MagicMock()
        server._remote_chat = MagicMock()

        server.ingest_robot_state(device.device_id, {'mode': 'idle'})
        command.refresh_from_db()
        self.assertEqual(command.status, 'sent')

        server.ingest_robot_state(device.device_id, {'mode': 'active'})
        command.refresh_from_db()
        self.assertEqual(command.status, 'confirmed')

    def test_remote_chat_activity_supplies_active_mode_fallback(self):
        server = MagicMock()
        remote = RemoteChat(server)

        remote.handle_request('d_active', {
            'command': 'notify', 'module_id': 'UNKNOWN', 'content_id': 'default',
        }, {})

        server.robot_data.return_value.note_mode.assert_called_once_with('d_active', 'active')


class WakeControlTests(TestCase):
    def setUp(self):
        self.schedule = MoxieSchedule.objects.create(name="test", schedule={"provided_schedule": []})
        self.device = MoxieDevice.objects.create(device_id="d_wake", schedule=self.schedule)

    @patch("hive.views.get_instance")
    def test_wake_enables_button_support_before_sending_command(self, get_instance):
        service = get_instance.return_value
        service.send_wakeup_to_bot.return_value = True

        response = self.client.post(reverse("hive:moxie_wake", args=[self.device.pk]))

        self.assertEqual(response.status_code, 302)
        self.device.refresh_from_db()
        self.assertTrue(self.device.robot_config["wake_button_enabled"])
        service.handle_config_updated.assert_called_once()
        service.send_wakeup_to_bot.assert_called_once_with("d_wake")

    @patch("hive.views.get_instance")
    def test_wake_chat_creates_chat_wake_schedule(self, get_instance):
        get_instance.return_value.send_wakeup_to_bot.return_value = True

        response = self.client.post(reverse("hive:moxie_wake_chat", args=[self.device.pk]))

        self.assertEqual(response.status_code, 302)
        self.device.refresh_from_db()
        self.assertEqual(
            self.device.schedule.schedule["wake_module"],
            {"module_id": "OPENMOXIE_CHAT", "content_id": "default"},
        )

    @patch("hive.views.get_instance")
    def test_trivia_control_refreshes_schedule_and_interrupts_before_launch(self, get_instance):
        service = get_instance.return_value
        service.robot_data.return_value.device_online.return_value = True
        service.queue_remote_action_to_bot.return_value = True
        self.device.robot_config = {'moxie_mode': 'TELEHEALTH'}
        self.device.save(update_fields=['robot_config'])

        response = self.client.post(reverse('hive:robot_control', args=[self.device.pk]), {'action': 'trivia'})

        self.assertEqual(response.status_code, 302)
        self.device.refresh_from_db()
        self.assertEqual(self.device.schedule.schedule['wake_module']['module_id'], 'OPENMOXIE_TRIVIA')
        self.assertNotIn('moxie_mode', self.device.robot_config)
        service.robot_data.return_value.schedule_update_live.assert_called_once_with(self.device)
        service.send_telehealth_interrupt.assert_called_once_with('d_wake')
        service.queue_remote_action_to_bot.assert_called_once_with(
            'd_wake', 'launch', 'OPENMOXIE_TRIVIA', 'default',
            'Trivia time! Get your thinking cap ready.',
        )
        service.send_remote_action_to_bot.assert_not_called()

    @patch("hive.views.get_instance")
    def test_homework_control_launches_answer_first_module(self, get_instance):
        service = get_instance.return_value
        service.robot_data.return_value.device_online.return_value = True
        service.queue_remote_action_to_bot.return_value = True

        response = self.client.post(reverse('hive:robot_control', args=[self.device.pk]), {'action': 'homework'})

        self.assertEqual(response.status_code, 302)
        self.device.refresh_from_db()
        self.assertEqual(self.device.schedule.schedule['wake_module']['module_id'], 'OPENMOXIE_HOMEWORK')
        service.queue_remote_action_to_bot.assert_called_once_with(
            'd_wake', 'launch', 'OPENMOXIE_HOMEWORK', 'default',
            'Homework mode is ready. Tell me the problem or subject.',
        )
        service.send_remote_action_to_bot.assert_not_called()

    @patch("hive.views.get_instance")
    def test_sleep_queues_router_action_interrupts_and_nudges_robot(self, get_instance):
        service = get_instance.return_value
        service.robot_data.return_value.device_online.return_value = True
        service.queue_remote_action_to_bot.return_value = True

        response = self.client.post(reverse('hive:robot_control', args=[self.device.pk]), {'action': 'sleep'})

        self.assertEqual(response.status_code, 302)
        service.queue_remote_action_to_bot.assert_called_once_with('d_wake', 'sleep', text='Okay. Good night!')
        service.send_telehealth_interrupt.assert_called_once_with('d_wake')
        service.send_wakeup_to_bot.assert_called_once_with('d_wake')
        service.send_remote_action_to_bot.assert_not_called()

    @patch("hive.views.get_instance")
    def test_chat_style_dashboard_controls_queue_a_real_router_response(self, get_instance):
        service = get_instance.return_value
        service.robot_data.return_value.device_online.return_value = True
        for action in ('wake', 'chat'):
            with self.subTest(action=action):
                service.reset_mock()
                service.robot_data.return_value.device_online.return_value = True
                response = self.client.post(
                    reverse('hive:robot_control', args=[self.device.pk]),
                    {'action': action},
                )

                self.assertEqual(response.status_code, 302)
                service.send_remote_action_to_bot.assert_not_called()
                self.assertEqual(
                    service.queue_remote_action_to_bot.call_args.args[2],
                    'OPENMOXIE_CHAT',
                )

    def test_removed_stop_alias_is_rejected(self):
        response = self.client.post(
            reverse('hive:robot_control', args=[self.device.pk]),
            {'action': 'stop'},
        )
        self.assertEqual(response.status_code, 400)

    @patch("hive.views.get_instance")
    def test_duplicate_transition_is_debounced(self, get_instance):
        service = get_instance.return_value
        service.robot_data.return_value.device_online.return_value = True

        first = self.client.post(
            reverse('hive:robot_control', args=[self.device.pk]),
            {'action': 'wake', 'ajax': '1'},
        )
        service.reset_mock()
        second = self.client.post(
            reverse('hive:robot_control', args=[self.device.pk]),
            {'action': 'wake', 'ajax': '1'},
        )

        self.assertEqual(first.status_code, 200)
        self.assertTrue(second.json()['duplicate'])
        self.assertEqual(RobotCommandEvent.objects.filter(action='wake').count(), 1)
        service.queue_remote_action_to_bot.assert_not_called()

    @patch("hive.views.get_instance")
    def test_new_transition_supersedes_stale_sent_command(self, get_instance):
        service = get_instance.return_value
        service.robot_data.return_value.device_online.return_value = True
        stale = RobotCommandEvent.objects.create(
            device=self.device, action='homework', label='Start homework', status='sent',
        )

        response = self.client.post(
            reverse('hive:robot_control', args=[self.device.pk]),
            {'action': 'wake', 'ajax': '1'},
        )

        stale.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(stale.status, 'failed')
        self.assertIn('Superseded', stale.detail)


class LocalAIAndMissionTests(TestCase):
    @patch.object(ai_factory._CHAT_HTTP_SESSION, 'post')
    def test_lmstudio_respects_configured_output_limit(self, post):
        ai_factory.configure_ai(
            chat_provider='lmstudio',
            chat_base_url='http://lmstudio.test/v1',
            chat_model='local-model',
        )
        response = post.return_value
        response.json.return_value = {
            'output': [{'type': 'message', 'content': 'A short answer.'}],
            'stats': {'input_tokens': 10, 'total_output_tokens': 4},
        }

        result = ai_factory.chat_completion(
            [{'role': 'user', 'content': 'Hello'}], max_tokens=35,
        )

        self.assertEqual(result, 'A short answer.')
        self.assertEqual(post.call_args.kwargs['json']['max_output_tokens'], 35)
        self.assertEqual(post.call_args.kwargs['json']['reasoning'], 'off')
        self.assertEqual(post.call_args.kwargs['timeout'], (5, 90))

    @patch.object(ai_factory._CHAT_HTTP_SESSION, 'post')
    def test_lmstudio_accepts_homework_reasoning_mode(self, post):
        ai_factory.configure_ai(
            chat_provider='lmstudio',
            chat_base_url='http://lmstudio.test/v1',
            chat_model='local-model',
        )
        post.return_value.json.return_value = {
            'output': [{'type': 'message', 'content': 'The answer is 42.'}],
        }

        ai_factory.chat_completion(
            [{'role': 'user', 'content': 'Solve it'}],
            max_tokens=512,
            reasoning='on',
        )

        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['max_output_tokens'], 512)
        self.assertEqual(payload['reasoning'], 'on')

    @patch("hive.views.get_instance")
    def test_setup_saves_independent_local_chat_and_stt_choices(self, get_instance):
        response = self.client.post(reverse('hive:hive_configure'), {
            'apikey': '', 'googleapikey': '', 'hostname': 'moxie-pc',
            'chat_provider': 'lmstudio',
            'chat_base_url': 'http://host.docker.internal:1234/v1',
            'chat_model': 'qwen-local',
            'stt_provider': 'local',
            'local_stt_model': 'small.en',
        })

        self.assertEqual(response.status_code, 302)
        config = HiveConfiguration.objects.get(name='default')
        self.assertEqual(config.chat_provider, 'lmstudio')
        self.assertEqual(config.stt_provider, 'local')

    def test_history_limit_mutates_the_actual_history(self):
        session = ChatSession(max_history=2)
        session.add_history('user', 'one')
        session.add_history('assistant', 'two')
        session.add_history('user', 'three')

        self.assertEqual([item['content'] for item in session._history], ['two', 'three'])

    def test_zero_question_probability_enforces_answer_only_context(self):
        session = SingleContextChatSession(
            prompt='Answer homework quickly.', question_probability=0.0,
        )
        volley = Volley.request_from_speech(
            'What is 12 times 8?', device_id='test',
            module_id='OPENMOXIE_HOMEWORK', content_id='default',
        )

        context = session.make_volley_context(volley)[0]['content']

        self.assertIn('Do not ask the person any questions', context)
        self.assertNotIn('End this response with one short, friendly question', context)

    def test_persistent_memory_is_not_duplicated_after_session_starts(self):
        session = SingleContextChatSession(prompt='Be concise.')
        session.add_history('assistant', 'Current session response.')
        volley = Volley.request_from_speech('Continue', device_id='test')
        volley._robot_data = {
            'persist': {'conversation_memory': {'recent': [
                {'role': 'assistant', 'content': 'Old remembered response.'},
            ]}},
            'conversation_memory_enabled': True,
        }

        context = session.make_volley_context(volley)[0]['content']

        self.assertNotIn('Old remembered response', context)

    def test_homework_solves_spoken_arithmetic_without_ai(self):
        homework = SinglePromptChat.objects.get(
            module_id='OPENMOXIE_HOMEWORK', content_id='default'
        )
        session = HomeworkChatSession(homework.pk)
        volley = Volley.request_from_speech(
            'What is fourteen plus eighteen?', device_id='test',
            module_id='OPENMOXIE_HOMEWORK', content_id='default',
        )

        with patch('hive.mqtt.conversations.chat_completion') as completion:
            session.handle_volley(volley)

        self.assertEqual(volley.response['output']['text'], '32.')
        completion.assert_not_called()

    def test_homework_uses_larger_budget_and_reasoning(self):
        homework = SinglePromptChat.objects.get(
            module_id='OPENMOXIE_HOMEWORK', content_id='default'
        )
        session = HomeworkChatSession(homework.pk)
        volley = Volley.request_from_speech(
            'Explain why the quadratic formula works.', device_id='test',
            module_id='OPENMOXIE_HOMEWORK', content_id='default',
        )

        with patch('hive.mqtt.conversations.chat_completion', return_value='It follows by completing the square.') as completion:
            session.handle_volley(volley)

        self.assertEqual(completion.call_args.kwargs['max_tokens'], 512)
        self.assertEqual(completion.call_args.kwargs['reasoning'], 'on')

    def test_homework_removes_questions_and_extra_offers(self):
        homework = SinglePromptChat.objects.get(
            module_id='OPENMOXIE_HOMEWORK', content_id='default'
        )
        session = HomeworkChatSession(homework.pk)
        volley = Volley.request_from_speech(
            'Explain photosynthesis.', device_id='test',
            module_id='OPENMOXIE_HOMEWORK', content_id='default',
        )

        with patch('hive.mqtt.conversations.chat_completion', return_value=(
            'Plants use sunlight to turn water and carbon dioxide into sugar. '
            'Would you like another example? I can also explain chlorophyll.'
        )):
            session.handle_volley(volley)

        self.assertEqual(
            volley.response['output']['text'],
            'Plants use sunlight to turn water and carbon dioxide into sugar.',
        )
        self.assertNotIn('?', volley.response['output']['text'])

    def test_trivia_scores_correct_answer_and_asks_next_question(self):
        device = MoxieDevice.objects.create(device_id='test', trivia_categories=['Test'])
        TriviaQuestion.objects.create(category='Test', question='What planet do we live on?', accepted_answers=['earth'])
        TriviaQuestion.objects.create(category='Test', question='What is two plus two?', accepted_answers=['four', '4'])
        session = TriviaChatSession()
        opener = Volley.request_from_speech('', device_id=device.device_id, module_id='OPENMOXIE_TRIVIA', content_id='default')
        session.handle_volley(opener)
        correct_answer = session.local_data['trivia_questions'][0]['answers'][0]
        answer = Volley.request_from_speech(correct_answer, device_id=device.device_id, module_id='OPENMOXIE_TRIVIA', content_id='default')
        session.handle_volley(answer)

        self.assertEqual(session.local_data['trivia_score'], 1)
        self.assertIn('Question 2', answer.response['output']['text'])

    @patch("hive.views.get_instance")
    def test_launcher_sets_selected_remote_mission_as_wake_module(self, get_instance):
        schedule = MoxieSchedule.objects.create(name='base', schedule={'provided_schedule': []})
        device = MoxieDevice.objects.create(device_id='d_launch', schedule=schedule)
        SinglePromptChat.objects.create(name='Trivia', module_id='OPENMOXIE_TRIVIA', content_id='default', opener='Hi', prompt='Trivia')
        get_instance.return_value.send_wakeup_to_bot.return_value = False

        response = self.client.post(reverse('hive:launch_mission', args=[device.pk]), {
            'module_id': 'OPENMOXIE_TRIVIA', 'content_id': 'default',
        })

        self.assertEqual(response.status_code, 302)
        device.refresh_from_db()
        self.assertEqual(device.schedule.schedule['wake_module'], {
            'module_id': 'OPENMOXIE_TRIVIA', 'content_id': 'default',
        })

    def test_tips_are_disabled_by_default_and_filtered_from_old_schedules(self):
        device = MoxieDevice.objects.create(device_id='d_rotation')
        schedule = {
            'provided_schedule': [{'module_id': 'TNT'}, {'module_id': 'DM'}],
            'generate': {'module_count': 0, 'chat_count': 0},
        }

        expanded = expand_schedule(schedule, device.device_id)

        self.assertEqual(device.disabled_module_ids, ['TNT'])
        self.assertNotIn('TNT', [item['module_id'] for item in expanded['provided_schedule']])
        self.assertIn('DM', [item['module_id'] for item in expanded['provided_schedule']])

    @patch('hive.views.get_instance')
    def test_rotation_manager_saves_disabled_missions_and_stories(self, get_instance):
        device = MoxieDevice.objects.create(device_id='d_rotation_save')
        get_instance.return_value.robot_data.return_value.schedule_update_live.return_value = True

        response = self.client.post(
            reverse('hive:mission_edit', args=[device.pk]),
            {'mission_action': 'save_rotation', 'included_modules': ['DM', 'JOKE']},
            follow=True,
        )
        device.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('DM', device.disabled_module_ids)
        self.assertNotIn('JOKE', device.disabled_module_ids)
        self.assertIn('TNT', device.disabled_module_ids)
        self.assertIn('STORY', device.disabled_module_ids)
        self.assertContains(response, 'Activity rotation saved.')


class ParentSafetyAndVoiceTests(TestCase):
    def setUp(self):
        self.device = MoxieDevice.objects.create(
            device_id='d_parent', name='Family Moxie', speaker_names=['Avery', 'Mom'],
        )

    def test_play_trivia_voice_command_returns_launch_action(self):
        responses = GlobalResponses()
        responses.update_from_database()
        volley = Volley.request_from_speech('Moxie, play trivia', device_id=self.device.device_id)

        functor = responses.check_global(volley)
        payload = functor()

        self.assertEqual(payload['response_action']['action'], 'launch')
        self.assertEqual(payload['response_action']['module_id'], 'OPENMOXIE_TRIVIA')

    def test_start_homework_voice_command_returns_launch_action(self):
        responses = GlobalResponses()
        responses.update_from_database()
        volley = Volley.request_from_speech('Moxie homework mode', device_id=self.device.device_id)

        payload = responses.check_global(volley)()

        self.assertEqual(payload['response_action']['action'], 'launch')
        self.assertEqual(payload['response_action']['module_id'], 'OPENMOXIE_HOMEWORK')

    def test_sleep_voice_command_accepts_trailing_please(self):
        responses = GlobalResponses()
        responses.update_from_database()
        volley = Volley.request_from_speech('Go to sleep, please.', device_id=self.device.device_id)

        payload = responses.check_global(volley)()

        self.assertEqual(payload['response_action']['action'], 'sleep')

    def test_pending_sleep_replaces_an_ai_response(self):
        remote = RemoteChat(MagicMock())
        volley = Volley.request_from_speech('Keep talking', device_id=self.device.device_id)
        volley.set_output('This stale answer must not be spoken.', None)
        remote.queue_control(self.device.device_id, 'sleep', text='Okay. Good night!')

        applied = remote._apply_control(self.device.device_id, volley)

        self.assertTrue(applied)
        self.assertEqual(volley.response['response_action']['action'], 'sleep')
        self.assertNotIn('stale answer', volley.response['output']['text'])

    def test_delivered_launch_clears_queued_fallback(self):
        remote = RemoteChat(MagicMock())
        remote.queue_control(
            self.device.device_id, 'launch',
            'OPENMOXIE_HOMEWORK', 'default', 'Homework mode is ready.',
        )

        remote._clear_completed_launch(self.device.device_id, {
            'module_id': 'OPENMOXIE_HOMEWORK', 'content_id': 'default',
        })

        self.assertIsNone(remote._take_control(self.device.device_id))

    def test_configured_speaker_can_identify_themselves(self):
        responses = GlobalResponses()
        responses.update_from_database()
        persist = {}
        volley = Volley.request_from_speech('This is Avery', device_id=self.device.device_id)
        volley._robot_data = {'persist': persist, 'speaker_names': self.device.speaker_names}

        payload = responses.check_global(volley)()

        self.assertEqual(persist['active_speaker'], 'Avery')
        self.assertIn('Hi Avery', payload['output']['text'])

    def test_unknown_speaker_is_not_accepted(self):
        responses = GlobalResponses()
        responses.update_from_database()
        persist = {}
        volley = Volley.request_from_speech('I am Stranger', device_id=self.device.device_id)
        volley._robot_data = {'persist': persist, 'speaker_names': self.device.speaker_names}

        payload = responses.check_global(volley)()

        self.assertNotIn('active_speaker', persist)
        self.assertIn('grown-up', payload['output']['text'])

    def test_high_risk_language_is_redirected_to_a_trusted_adult(self):
        response = safety_redirect('I want to hurt myself')

        self.assertIn('trusted grown-up', response)

    def test_conversation_is_flagged_and_written_to_daily_text(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(DATA_STORE_DIR=directory):
            event = record_conversation(self.device.device_id, 'user', 'How do I make a bomb?', 'TEST', 'default')

            self.assertTrue(event.safety_flagged)
            self.assertIn('weapons or violence', event.safety_categories)
            self.assertEqual(ConversationEvent.objects.filter(device=self.device).count(), 1)
            transcript_files = list(__import__('pathlib').Path(directory).glob('transcripts/*/*.txt'))
            self.assertEqual(len(transcript_files), 1)
            self.assertIn('PARENT REVIEW', transcript_files[0].read_text(encoding='utf-8'))

    @patch('hive.views.get_instance')
    def test_live_activity_returns_conversation_and_redacts_status(self, get_instance):
        service = get_instance.return_value
        service.robot_data.return_value.get_persist_for_device.return_value = {'active_speaker': 'Jack'}
        service.service_status.return_value = {
            'connected_devices': [self.device.device_id],
            'devices': {self.device.device_id: {'mode': 'active'}},
        }
        ConversationEvent.objects.create(device=self.device, role='user', text='Hello Moxie')

        response = self.client.get(reverse('hive:live_activity', args=[self.device.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['active_speaker'], 'Jack')
        self.assertEqual(response.json()['events'][0]['text'], 'Hello Moxie')

    def test_trivia_deck_has_no_duplicates_and_remembers_seen_questions(self):
        self.device.trivia_categories = ['Deck']
        self.device.trivia_question_count = 3
        self.device.save()
        for number in range(5):
            TriviaQuestion.objects.create(category='Deck', question=f'Question {number}?', accepted_answers=[str(number)])

        first = TriviaChatSession()
        first.handle_volley(Volley.request_from_speech('', device_id=self.device.device_id, module_id='OPENMOXIE_TRIVIA', content_id='default'))
        first_ids = [item['id'] for item in first.local_data['trivia_questions']]
        self.device.refresh_from_db()

        self.assertEqual(len(first_ids), len(set(first_ids)))
        self.assertEqual(set(first_ids), set(self.device.trivia_seen_question_ids))

    def test_joke_session_does_not_repeat_a_joke(self):
        Joke.objects.all().delete()
        for number in range(3):
            Joke.objects.create(collection='Test', setup=f'Setup {number}?', punchline=f'Punchline {number}.')
        session = JokeChatSession()
        prompt = Volley.request_from_speech('', device_id=self.device.device_id, module_id='OPENMOXIE_JOKES', content_id='default')
        session.handle_volley(prompt)

        self.assertEqual(len(session.local_data['jokes']), 3)
        self.assertEqual(len({item['setup'] for item in session.local_data['jokes']}), 3)

    @patch('hive.views.get_instance')
    def test_transcript_entry_can_be_deleted_and_text_file_is_rewritten(self, get_instance):
        get_instance.return_value.robot_data.return_value.get_persist_for_device.return_value = {}
        with tempfile.TemporaryDirectory() as directory, override_settings(DATA_STORE_DIR=directory):
            first = record_conversation(self.device.device_id, 'user', 'Keep me')
            second = record_conversation(self.device.device_id, 'moxie', 'Remove me')
            response = self.client.post(reverse('hive:transcript_manage', args=[self.device.pk]), {
                'action': 'delete_event', 'event_id': second.pk,
            })
            transcript = next(__import__('pathlib').Path(directory).glob('transcripts/*/*.txt')).read_text(encoding='utf-8')

            self.assertEqual(response.status_code, 302)
            self.assertTrue(ConversationEvent.objects.filter(pk=first.pk).exists())
            self.assertFalse(ConversationEvent.objects.filter(pk=second.pk).exists())
            self.assertIn('Keep me', transcript)
            self.assertNotIn('Remove me', transcript)

    @patch('hive.views.get_instance')
    def test_voice_controls_are_saved_to_robot_settings(self, get_instance):
        schedule = MoxieSchedule.objects.create(name='voice', schedule={'provided_schedule': []})
        response = self.client.post(reverse('hive:moxie_edit', args=[self.device.pk]), {
            'moxie_name': 'Family Moxie', 'nickname': 'Avery', 'speaker_names': 'Avery',
            'conversation_profile': 'Friendly', 'schedule': schedule.pk, 'screen_brightness': '1',
            'audio_volume': '.6', 'pairing_status': 'paired', 'tts_voice': 'Ivy',
            'tts_speech_rate': '92',
        })
        self.device.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.device.robot_settings['props']['cloud_tts_voice_id'], 'Ivy')
        self.assertEqual(self.device.robot_settings['props']['cloud_tts_speech_rate'], '92')

    @patch('hive.views.get_instance')
    def test_parent_corner_pages_render(self, get_instance):
        get_instance.return_value.robot_data.return_value.get_config_for_device.return_value = {
            'audio_volume': .6, 'screen_brightness': 1, 'child_pii': {'nickname': 'Avery'},
        }
        get_instance.return_value.robot_data.return_value.device_online.return_value = True
        for route in ('monitor', 'transcripts', 'trivia_settings', 'joke_settings', 'moxie'):
            with self.subTest(route=route):
                response = self.client.get(reverse(f'hive:{route}', args=[self.device.pk]))
                self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse('hive:guide')).status_code, 200)

        trivia = self.client.get(reverse('hive:trivia_settings', args=[self.device.pk]))
        self.assertContains(trivia, 'id="library-category"')
        rotation = self.client.get(reverse('hive:moxie_missions', args=[self.device.pk]))
        self.assertContains(rotation, 'Tips &amp; tricks are off by default.')
        self.assertContains(rotation, 'data-module="STORY"')

    def test_starter_libraries_exceed_alpha_targets_and_are_unique(self):
        self.assertGreaterEqual(Joke.objects.count(), 100)
        self.assertEqual(Joke.objects.count(), Joke.objects.values('setup').distinct().count())
        self.assertGreaterEqual(TriviaQuestion.objects.count(), 200)
        self.assertEqual(
            TriviaQuestion.objects.count(),
            TriviaQuestion.objects.values('question').distinct().count(),
        )

    def test_trivia_save_shows_animated_confirmation(self):
        response = self.client.post(
            reverse('hive:trivia_configure', args=[self.device.pk]),
            {'action': 'save_options', 'question_count': '12', 'categories': ['Science']},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'save-toast')
        self.assertContains(response, 'Trivia mix saved and ready for the next game.')
