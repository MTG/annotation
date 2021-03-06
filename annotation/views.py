import os
import json
import datetime
import zipfile
import shutil

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

from .models import AnnotationSimilarity, Annotation, Exercise, Sound, Tier, DataSet, Tag, Complete
from .forms import TierForm


@login_required
def data_set_list(request):
    data_sets_list = request.user.datasets.all()
    context = {'data_sets_list': data_sets_list}
    return render(request, 'annotationapp/data_sets_list.html', context)


@login_required
def exercise_list(request, dataset_id):
    data_set = DataSet.objects.get(id=dataset_id)
    exercises_list = data_set.exercises.all().order_by('-created_at')
    # get data set statistics
    number_of_sounds = Sound.objects.filter(exercise__in=Exercise.objects.filter(data_set=data_set)).count()
    number_of_completed_sounds = Sound.objects.filter(exercise__in=Exercise.objects.filter(data_set=data_set)).\
        filter(annotation_state='C').count()
    current_date = datetime.datetime.today()
    last_week_segments = Annotation.objects.filter(
        created_at__range=[current_date - datetime.timedelta(days=7),
                           current_date]).filter(sound__exercise__data_set=data_set).count()
    last_week_similarity_annotations = AnnotationSimilarity.objects.filter(
        created_at__range=[current_date - datetime.timedelta(days=7), current_date]).count()
    context = {'exercises_list': exercises_list, 'data_set': data_set,
               'number_of_completed_sounds': number_of_completed_sounds,
               'number_of_sounds': number_of_sounds,
               'last_week_segments': last_week_segments,
               'last_week_similarity_annotations': last_week_similarity_annotations}
    return render(request, 'annotationapp/exercises_list.html', context)


@login_required
def tier_delete(request, exercise_id, tier_id, sound_id):
    exercise = Exercise.objects.get(id=exercise_id)
    tier = exercise.tiers.get(id=tier_id)
    if request.method == 'POST':
        tier.delete()
        return redirect(reverse('tier_list', kwargs={
            'exercise_id': exercise_id,
            'sound_id': sound_id
            }))
    context = {'exercise': exercise, 'tier': tier, 'sound_id': sound_id}
    return render(request, 'annotationapp/tier_delete.html', context)


@login_required
@csrf_exempt
def check_tiers_ajax(request, exercise_id):
    if request.method == 'POST':
        point = request.POST.get('point')
        parent = request.POST.get('parent', None)
        sync = request.POST.get('sync', None)

        exercise = Exercise.objects.get(id=exercise_id)
        tiers_list = exercise.tiers
        parent_list = exercise.tiers
        if point == 'true':
            parent_list = parent_list.exclude(point_annotations=False)
            tiers_list = tiers_list.exclude(point_annotations=False)
        if parent:
            tiers_list = tiers_list.exclude(id=parent)
        if sync:
            parent_list = parent_list.exclude(id=sync)

        ret = {
            'sync_tiers': list(tiers_list.values_list('id', 'name')),
            'parent_tiers': list(parent_list.values_list('id', 'name'))
            }
        return JsonResponse(ret)


@login_required
def tier_edit(request, exercise_id, tier_id, sound_id):
    exercise = Exercise.objects.get(id=exercise_id)
    tiers_list = exercise.tiers.all()
    tier = tiers_list.get(id=tier_id)
    if request.method == 'POST':
        tier_form = TierForm(request.POST)
        if tier_form.is_valid():
            tier_name = request.POST['name']
            parent_tier_id = request.POST['parent_tier']
            if parent_tier_id:
                parent_tier = Tier.objects.get(id=parent_tier_id)
                tier.parent_tier = parent_tier
            else:
                tier.parent_tier = None

            special_parent_tier_id = request.POST['special_parent_tier']
            if special_parent_tier_id:
                special_aprent_tier = Tier.objects.get(id=special_parent_tier_id)
                tier.special_parent_tier = special_aprent_tier
            else:
                tier.special_parent_tier = None

            tier.name = tier_name
            tier.exercise = exercise
            tier.similarity_keys = tier_form.cleaned_data['dimensions']

            # if point_annotations attribute is changed, delete previous annotations
            if ('point_annotations' in request.POST) != tier.point_annotations:
                tier.annotations.all().delete()
            tier.point_annotations = 'point_annotations' in request.POST
            tier.save()
            return redirect(reverse('tier_list', kwargs={
                'exercise_id': exercise_id,
                'sound_id': sound_id
                }))
    else:
        tiers_list_ids = tiers_list.values_list('id')
        tier_form = TierForm(instance=tier, parent_tier_ids=tiers_list_ids)
    context = {'exercise': exercise, 'tier': tier, 'form': tier_form}
    return render(request, 'annotationapp/tier_creation.html', context)


@login_required
def tier_list(request, exercise_id, sound_id):
    exercise = Exercise.objects.get(id=exercise_id)
    tiers_list = exercise.tiers.all().order_by('created_at')
    if request.method == 'POST':
        tier_form = TierForm(request.POST)
        if tier_form.is_valid():
            tier_name = request.POST['name']
            exercise = Exercise.objects.get(id=exercise_id)
            parent_tier_id = request.POST['parent_tier']
            parent_tier = None

            if parent_tier_id:
                parent_tier = Tier.objects.get(id=parent_tier_id)

            tier = Tier.objects.create(name=tier_name, exercise=exercise, parent_tier=parent_tier)
            tier.similarity_keys = tier_form.cleaned_data['dimensions']

            if 'point_annotations' in request.POST:
                tier.point_annotations = True

            tier.save()
    else:
        tiers_list_ids = tiers_list.values_list('id')
        tier_form = TierForm(parent_tier_ids=tiers_list_ids)
    sound = Sound.objects.get(id=sound_id)
    context = {'exercise': exercise, 'sound': sound, 'tiers_list': tiers_list, 'form': tier_form}
    # if the sound is the reference sound of the exercise, add a context parameter
    if sound == exercise.reference_sound:
        context['reference_sound'] = True
    return render(request, 'annotationapp/tiers_list.html', context)


@login_required
def sound_list(request, exercise_id):
    exercise = get_object_or_404(Exercise, id=exercise_id)
    display_filter = request.GET.get('filter', False)
    sounds_list = exercise.sounds
    if display_filter == 'discarded':
        sounds_list = sounds_list.filter(is_discarded=True)
    else:
        sounds_list = sounds_list.filter(is_discarded=False)
    context = {'display_filter': display_filter, 'exercise': exercise}
    if exercise is Http404:
        return render(request, exercise)
    if request.method == 'POST':
        reference_sound_id = request.POST['reference sound']
        sound = Sound.objects.get(id=reference_sound_id)
        exercise.reference_sound = sound
        exercise.save()
    else:
        if not exercise.reference_sound:
            return render(request, 'annotationapp/select_reference.html', context)
        else:
            reference_sound = exercise.reference_sound
            sounds_list = sounds_list.exclude(id=reference_sound.id)

            completes = Complete.objects.filter(sound__in=sounds_list, user=request.user)

            completed_sounds = {complete.sound_id: True for complete in completes}
            sounds_list_plus_data = [{"sound": sound, "is_completed": completed_sounds.get(sound.id, False)} for sound
                                     in sounds_list]
            paginator = Paginator(sounds_list_plus_data, 20)
            page = request.GET.get('page')
            try:
                sounds = paginator.page(page)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                sounds = paginator.page(1)
            except EmptyPage:
                # If page is out of range (e.g. 9999), deliver last page of results.
                sounds = paginator.page(paginator.num_pages)
            context['sounds_list'] = sounds
            context['tier'] = exercise.tiers.all()[0]
            context['user'] = request.user
            if display_filter != 'discarded':
                context['reference_sound'] = reference_sound
    return render(request, 'annotationapp/sounds_list.html', context)


@login_required
def sound_detail(request, exercise_id, sound_id, tier_id):
    sound = get_object_or_404(Sound, id=sound_id)
    if request.method == 'POST':
        if sound.is_discarded:
            sound.is_discarded = False
        else:
            sound.is_discarded = True
        sound.save()
        return redirect('/' + exercise_id + '/sound_list')
    tier = get_object_or_404(Tier, id=tier_id)
    other_tiers = sound.exercise.tiers.all().order_by('created_at')
    context = {'sound': sound, 'tier': tier, 'other_tiers': other_tiers, 'exercise_id': exercise_id}
    return render(request, 'annotationapp/sound_detail.html', context)


@login_required
def ref_sound_detail(request, exercise_id, sound_id, tier_id):
    if request.method == 'POST':
        tier_form = TierForm(request.POST)
        if tier_form.is_valid():
            tier_name = request.POST['name']
            exercise = Exercise.objects.get(id=exercise_id)
            Tier.objects.create(name=tier_name, exercise=exercise)
    else:
        tier_form = TierForm()

    sound = get_object_or_404(Sound, id=sound_id)

    tier = Tier.objects.get(id=tier_id)
    other_tiers = sound.exercise.tiers.all().order_by('created_at')
    context = {'form': tier_form, 'sound': sound, 'tier': tier, 'other_tiers': other_tiers, 'exercise_id': exercise_id}
    return render(request, 'annotationapp/ref_sound_annotation.html', context)


@login_required
@csrf_exempt
def annotation_action(request, sound_id, tier_id):
    sound = get_object_or_404(Sound, id=sound_id)
    tier = get_object_or_404(Tier, id=tier_id)
    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        post_body = json.loads(body_unicode)

        sound.update_annotations(tier, post_body['annotations'], request.user)

        return JsonResponse({'status': 'success'})
    else:
        tags = Tag.objects.filter(tiers=tier).values_list('name', flat=True).all()
        ref_sound = sound.exercise.reference_sound
        out = {
            "task": {
                "feedback": "none",
                "visualization": "waveform",
                "similaritySegment": ["yes", "no"],
                "similarityKeys": tier.similarity_keys,
                "annotationTags": list(tags),
                "alwaysShowTags": False
            }
        }
        if request.GET.get('enable_spec', None):
            out['task']['visualization'] = "spectrogram"

        out['task']['segments_ref'] = ref_sound.get_annotations_for_tier(tier)
        out['task']['segments'] = sound.get_annotations_for_tier(tier, request.user)
        out['task']['url'] = os.path.join(settings.MEDIA_URL, sound.exercise.data_set.name, sound.exercise.name,
                                          sound.filename)
        out['task']['url_ref'] = os.path.join(settings.MEDIA_URL, sound.exercise.data_set.name, sound.exercise.name,
                                              ref_sound.filename)
        return JsonResponse(out)


@login_required
def download_annotations(request, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)

    ret = sound.get_annotations_as_dict()
    return JsonResponse(ret)


@login_required
def tier_creation(request, exercise_id, sound_id):
    exercise = Exercise.objects.get(id=exercise_id)
    tiers_list = exercise.tiers.all()
    if request.method == 'POST':
        tier_form = TierForm(request.POST)
        if tier_form.is_valid():
            tier_name = request.POST['name']
            exercise = Exercise.objects.get(id=exercise_id)
            parent_tier_id = request.POST['parent_tier']
            if parent_tier_id:
                parent_tier = Tier.objects.get(id=parent_tier_id)
                tier = Tier.objects.create(name=tier_name, exercise=exercise, parent_tier=parent_tier)
            else:
                tier = Tier.objects.create(name=tier_name, exercise=exercise)
            special_parent_tier_id = request.POST['special_parent_tier']
            if special_parent_tier_id:
                special_parent_tier = Tier.objects.get(id=special_parent_tier_id)
                tier.special_parent_tier = special_parent_tier
            if 'point_annotations' in request.POST:
                tier.point_annotations = True
            tier.similarity_keys = tier_form.cleaned_data['dimensions']
            tier.save()
            return redirect('/' + exercise_id + '/' + sound_id + '/tiers_list')
    else:
        tiers_list_ids = tiers_list.values_list('id')
        tier_form = TierForm(parent_tier_ids=tiers_list_ids)
    context = {'form': tier_form, 'exercise': exercise, 'create': True}
    return render(request, 'annotationapp/tier_creation.html', context)


def download_data_set_annotations(request, data_set_id):
    """
    Download all the annotations of a data set
    Args:
        data_set_id: id of the dataset

    Returns:
        zip file containing a .json file for each sound in the data set containing the annotations
    """

    data_set = DataSet.objects.get(id=data_set_id)

    try:
        sounds = Sound.objects.filter(exercise__data_set=data_set)
    except ObjectDoesNotExist:
        return None

    # make directory for intermediate json files
    tmp_directory = os.path.join(settings.TEMP_ROOT, data_set.name + '_annotations')
    os.mkdir(tmp_directory)

    # create json files
    for sound in sounds:
        annotations = sound.get_annotations_as_dict()
        annotations_file_path = os.path.join(tmp_directory, os.path.splitext(sound.filename)[0] + '.json')
        with open(annotations_file_path, 'w') as fp:
            json.dump(annotations, fp)

    # create
    zip_file_path = tmp_directory + '.zip'
    zip_file = zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED)
    for annotation_file in os.listdir(tmp_directory):
        annotation_file_path = os.path.join(tmp_directory, annotation_file)
        zip_file.write(annotation_file_path, os.path.basename(annotation_file_path))
    zip_file.close()

    # remove json files
    shutil.rmtree(tmp_directory)

    response = HttpResponse(open(zip_file_path, 'rb'), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(zip_file_path)
    return response
