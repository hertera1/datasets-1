# coding=utf-8
# Copyright 2022 The TensorFlow Datasets Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ArrayRecord DataSource base class.

Warning: this is an experimental module. The interface might change in the
future without backwards compatibility.
"""

from collections.abc import Sequence as AbcSequence
import dataclasses
from typing import Optional, Sequence, TypeVar, Union

from tensorflow_datasets.core import dataset_info as dataset_info_lib
from tensorflow_datasets.core import decode
from tensorflow_datasets.core import file_adapters
from tensorflow_datasets.core import splits as splits_lib
from tensorflow_datasets.core.utils import type_utils
import tree

from array_record.python import array_record_data_source

T = TypeVar('T')


@dataclasses.dataclass
class ArrayRecordDataSource(AbcSequence):
  """Grain DataSource class.

  Warning: this is an experimental class. The interface might change in the
  future without backwards compatibility.

  It acts as a wrapper around `array_record.ArrayRecordDataSource` that can read
  from ArrayRecords. It exposes `__len__` and `__getitem__` to serve as a data
  source.
  """

  dataset_info: dataset_info_lib.DatasetInfo
  split: splits_lib.Split = None
  decoders: Optional[type_utils.TreeDict[decode.partial_decode.DecoderArg]] = (
      None
  )
  data_source: array_record_data_source.ArrayRecordDataSource = (
      dataclasses.field(init=False)
  )
  length: int = dataclasses.field(init=False)

  def __post_init__(self):
    file_format = self.dataset_info.file_format
    if file_format != file_adapters.FileFormat.ARRAY_RECORD:
      raise NotImplementedError(
          f'No random access data source for file format {file_format}. Please,'
          ' generate your data using `tfds.builder(...,'
          f' file_format={file_adapters.FileFormat.ARRAY_RECORD})`.'
      )
    if self.split not in self.dataset_info.splits:
      possible_splits = list(self.dataset_info.splits.keys())
      raise IndexError(f'Split "{self.split}" is not in {possible_splits}')
    file_instructions = self.dataset_info.splits[self.split].file_instructions
    self.data_source = array_record_data_source.ArrayRecordDataSource(
        file_instructions
    )
    self.length = len(self.data_source)

  def __len__(self) -> int:
    return self.length

  def __getitem__(
      self, record_keys: Union[int, Sequence[int]]
  ) -> Union[T, Sequence[T]]:
    has_requested_single_record = isinstance(record_keys, int)
    if has_requested_single_record:
      if record_keys >= self.length or record_keys < 0:
        raise IndexError('data source index out of range')
      record_keys = [record_keys]
    records = self.data_source[record_keys]
    features = self.dataset_info.features
    if len(record_keys) != len(records):
      raise IndexError(
          f'Requested {len(record_keys)} records but got'
          f' {len(records)} records.'
      )
    if has_requested_single_record:
      return features.deserialize_example_np(records[0], decoders=self.decoders)
    return [
        features.deserialize_example_np(record, decoders=self.decoders)
        for record in records
    ]

  def __repr__(self) -> str:
    decoders_repr = (
        tree.map_structure(type, self.decoders) if self.decoders else None
    )
    return (
        f'GrainDataSource(name={self.dataset_info.name}, '
        f'split={self.split!r}, '
        f'decoders={decoders_repr})'
    )
