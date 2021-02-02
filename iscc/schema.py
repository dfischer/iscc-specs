# -*- coding: utf-8 -*-
from enum import Enum
import mmap
from io import BufferedReader, BytesIO
from pathlib import Path
from typing import BinaryIO, List, Optional, Union
from pydantic import BaseSettings, BaseModel, Field


Data = Union[bytes, bytearray, memoryview]
Uri = Union[str, Path]
File = Union[BinaryIO, mmap.mmap, BytesIO, BufferedReader]
Readable = Union[Uri, Data, File]


DEFAULT_WINDOW = 7
DEFAULT_OVERLAP = 3
FEATURE_REGEX = "^[-A-Za-z0-9_]{11}"


class Opts(BaseSettings):
    """Options for ISCC generation"""

    meta_bits: int = Field(64, description="Length of generated Meta-ID in bits")
    meta_trim_title: int = Field(
        128, description="Trim title length to this mumber of bytes"
    )
    meta_trim_extra: int = Field(4096, description="Trim extra to this number of bytes")

    text_bits: int = Field(
        64, description="Length of generated Content-ID-Text in bits"
    )

    text_ngram_size: int = Field(
        13, description="Number of characters per feature hash (size of sliding window)"
    )

    text_granular: bool = Field(
        False, description="Calculate and return granular text features"
    )

    text_avg_chunk_size: int = Field(
        1024,
        description="Avg number of characters per text chunk for granular fingerprints",
    )

    image_bits: int = Field(
        64, description="Length of generated Content-ID-Image in bits"
    )

    image_trim: bool = Field(
        False,
        description="Autocrop empty borders of images before Image-Code generation",
    )

    image_preview: bool = Field(False, description="Generate image preview thumbnail")

    image_preview_size: int = Field(
        96, description="Size of larger side of thumbnail in pixels"
    )

    image_preview_quality: int = Field(
        30, description="Image compression setting (0-100)"
    )

    image_exif_transpose: bool = Field(
        True,
        description="Transpose according to EXIF Orientation tag before hashing",
    )

    audio_bits: int = Field(
        64, description="Length of generated Content-ID-Audio in bits"
    )

    audio_granular: bool = Field(
        False, description="Calculate and return granular audio features"
    )

    audio_max_duration: int = Field(
        120,
        description="Maximum seconds of audio to process",
    )

    video_bits: int = Field(
        64, description="Length of generated Content-ID-Video in bits"
    )

    video_fps: int = Field(
        5,
        description="Frames per second to process for video hash (ignored when 0).",
    )

    video_crop: bool = Field(
        True, description="Detect and remove black borders before processing"
    )

    video_granular: bool = Field(False, description="Generate granular features")

    video_scenes: bool = Field(
        False, description="Use scene detection for granular features"
    )

    video_scenes_fs: int = Field(
        2,
        description="Number of frames to skip per processing step for scene detection. "
        "Higher values will increase detection speed and decrease detection"
        " quality.",
    )

    video_scenes_th: int = Field(
        40,
        description="Threshold for scene detection. Higher values detect less scenes.",
    )

    video_scenes_min: int = Field(
        15,
        description="Minimum number of frames per scene.",
    )

    video_window: int = Field(
        7, description="Seconds of video per granular feature in rolling window mode"
    )

    video_overlap: int = Field(
        3, description="Seconds of video that overlap in roling window mode"
    )

    video_include_mp7sig: bool = Field(
        False, description="Include raw MPEG-7 Video Signature in output"
    )

    video_preview: bool = Field(
        False, description="Generate 128px video preview thumbnail(s)"
    )

    video_hwaccel: Optional[str] = Field(
        None, description="Use hardware acceleration for video processing"
    )

    data_bits: int = Field(64, description="Length of generated Data-Code in bits")

    instance_bits: int = Field(
        64, description="Length of generated Instance-Code in bits"
    )

    io_chunk_size: int = Field(
        524288, description="Number of bytes per io read operation"
    )


class Features(BaseModel):
    """Granular feature codes.

    If only a list of features is provided it is assumed that those have been created
    with the default values for 'window' and 'overlap'.

    If sizes are provided it is assumed that we deal with custom segment sizes
    based on content aware chunking.
    """

    features: List[str] = Field(
        description="Segmentwise 64-bit features (base64url encoded).",
        regex=FEATURE_REGEX,
        min_items=1,
    )
    window: Optional[int] = Field(
        DEFAULT_WINDOW,
        description="Window size of feature segments",
    )
    overlap: Optional[int] = Field(
        DEFAULT_OVERLAP,
        description="Overlap size of feature segments",
    )
    sizes: Optional[List[int]] = Field(
        description="Sizes of segmets used for feature calculation",
        min_items=1,
    )


class GMT(str, Enum):
    """Generic Metdia Type"""

    text = "text"
    image = "image"
    audio = "audio"
    video = "video"
    unknown = "unknown"


class ISCC(BaseModel):
    version: int = Field(0, description="ISCC Schema Version")
    iscc: str = Field(description="ISCC code of the identified digital asset.")
    title: Optional[str] = Field(
        description="The title or name of the intangible creation manifested by the"
        " identified digital asset"
    )
    extra: Optional[str] = Field(
        description="Descriptive, industry-sector or use-case specific metadata (used "
        "as immutable input for Meta-Code generation). Any text string "
        "(structured or unstructured) indicative of the identity of the "
        "referent may be used."
    )
    filename: Optional[str] = Field(
        description="Filename of the referenced digital asset (automatically used as "
        "fallback if no seed_title element is specified)"
    )
    identifier: Optional[str] = Field(
        description="Other identifier(s) such as those defined by ISO/TC 46/SC 9 "
        "referencing the work, product or other abstraction of which the "
        "referenced digital asset is a full or partial manifestation "
        "(automatically used as fallback if no extra element is specified)."
    )
    gmt: GMT = Field(GMT.unknown, description="Generic Media Type")
    language: Optional[List[str]] = Field(
        description="Language(s) of content (BCP-47) in weighted order."
    )
    characters: Optional[int] = Field(
        description="Number of text characters (code points after Unicode "
        "normalization) (GMT Text only)."
    )
    features: Optional[Features] = Field(
        description="GMT-specific standardized fingerprint for granular content "
        "recognition and matching purposes."
    )


if __name__ == "__main__":
    """Save ISCC JSON schema"""
    from os.path import abspath, dirname, join

    HERE = dirname(abspath(__file__))
    SCHEMA_PATH = join(HERE, "iscc.json")
    schema = ISCC.schema_json()
    with open(SCHEMA_PATH, "wt", encoding="UTF-8") as outf:
        outf.write(ISCC.schema_json(indent=2))
