from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Task, Report
from .constants import COMPLETED_STATUS, COMPLETED_LATE_STATUS, NOT_COMPLETED_STATUS
Curator = get_user_model()


class TaskCreateSerializer(serializers.Serializer):
    id_task = serializers.CharField(max_length=100)
    deadline = serializers.DateTimeField()
    name = serializers.CharField(max_length=200)
    description = serializers.CharField()
    report = serializers.CharField()

    subject_id = serializers.IntegerField(required=False)
    department_id = serializers.IntegerField(required=False)
    role_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )

    id_tg_list = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    single_id_tg = serializers.IntegerField(required=False)

    def validate(self, attrs):
        # Должно быть указано хоть что-то (группа или конкретный)
        if not any([attrs.get('subject_id'),
                    attrs.get('department_id'),
                    attrs.get('role_ids'),
                    attrs.get('id_tg_list'),
                    attrs.get('single_id_tg')]):
            raise serializers.ValidationError(
                'Нужно задать группу или конкретного куратор(а).')
        return attrs


class RecipientCuratorSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role.role', read_only=True)
    subject = serializers.CharField(source='subject.subject', read_only=True)
    department = serializers.CharField(
        source='department.department', read_only=True)

    class Meta:
        model = Curator
        fields = ('id_tg', 'name', 'role', 'subject', 'department')


class TaskCardSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='id_task')
    title = serializers.CharField(source='name')
    status = serializers.CharField(source='card_status')
    progress = serializers.IntegerField()
    completed = serializers.IntegerField()
    total = serializers.IntegerField()
    notCompleted = serializers.IntegerField(source='not_completed')
    deadline = serializers.DateTimeField()
    created = serializers.DateTimeField(
        required=False, allow_null=True)
    description = serializers.CharField()

    sampleCurators = serializers.SerializerMethodField()

    def get_sampleCurators(self, obj):
        arr = getattr(obj, 'sample_names', []) or []
        return arr[:3]

    class Meta:
        model = Task
        fields = ('id', 'title', 'status', 'progress', 'completed', 'total', 'notCompleted',
                  'deadline', 'created', 'description', 'sampleCurators')


STATUS_MAP = {
    COMPLETED_STATUS: 'completed',
    COMPLETED_LATE_STATUS:    'completed_late',
    NOT_COMPLETED_STATUS:     'not_completed',
}


class TaskDetailSerializer(serializers.ModelSerializer):
    id_tg = serializers.IntegerField(source='curator.id_tg', read_only=True)
    name = serializers.CharField(source='curator.name', read_only=True)
    role = serializers.CharField(source='curator.role.role', read_only=True)

    completedAt = serializers.DateTimeField(
        source='timestamp_end', allow_null=True, read_only=True)
    reportUrl = serializers.CharField(
        source='report_url', allow_null=True, read_only=True)
    reportText = serializers.CharField(
        source='report_text', allow_null=True, read_only=True)

    status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Report
        fields = ('id_tg', 'name', 'role', 'status',
                  'completedAt', 'reportUrl', 'reportText')

    def get_status(self, obj):
        return STATUS_MAP.get(getattr(obj, 'status_id', None), 'not_completed')


class ReportDetailSerializer(serializers.ModelSerializer):
    curator = serializers.CharField(source='curator.name', read_only=True)
    role = serializers.CharField(source='curator.role.role', read_only=True)
    task = serializers.CharField(source='task.name', read_only=True)
    deadline = serializers.DateTimeField(
        source='task.deadline', read_only=True)
    status = serializers.SerializerMethodField()
    completedAt = serializers.DateTimeField(
        source='timestamp_end', read_only=True)
    reportUrl = serializers.CharField(
        source='report_url', read_only=True, allow_null=True)
    reportText = serializers.CharField(
        source='report_text', read_only=True, allow_null=True)

    class Meta:
        model = Report
        fields = ('id_report', 'curator', 'role', 'task', 'status',
                  'completedAt', 'deadline', 'reportUrl', 'reportText')

    def get_status(self, obj):
        return STATUS_MAP.get(getattr(obj, 'status_id', None), 'not_completed')
