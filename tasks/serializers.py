from rest_framework import serializers
from django.contrib.auth import get_user_model
from tasks.models import Task

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
