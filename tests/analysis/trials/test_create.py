import uuid
from tests.analysis.utils import generate_data
from tornasole.trials import create_trial

def test_creation_local():
  trial_name = str(uuid.uuid4())
  path = 'ts_output/train/'
  num_steps = 20
  num_tensors = 10
  for i in range(num_steps):
    generate_data(path=path, trial=trial_name, num_tensors=num_tensors,
                  step=i, tname_prefix='foo', worker='algo-1', shape=(3, 3, 3))
  tr = create_trial(path + '/' + trial_name, range_steps=(0,5))
  assert len(tr.available_steps()) == 5

def test_creation_s3():
  trial_name = str(uuid.uuid4())
  path = 's3://tornasole-testing/rules/ts_output/train/'
  num_steps = 8
  num_tensors = 10
  for i in range(num_steps):
    generate_data(path=path, trial=trial_name, num_tensors=num_tensors,
                  step=i, tname_prefix='foo', worker='algo-1', shape=(3, 3, 3))
  tr = create_trial(path + trial_name, range_steps=(0,5))
  assert len(tr.available_steps()) == 5