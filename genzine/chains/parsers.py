import re
from difflib import SequenceMatcher
from random import randrange
from string import punctuation

import numpy as np
from fastembed import TextEmbedding
from scipy.spatial.distance import cdist

from genzine.utils import LOG, strip_and_lower

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import BaseOutputParser

EMBEDDING_MODEL = TextEmbedding()


class CosineSimilarityOutputParser(BaseOutputParser[str]):
    """Custom similarity parser.

    Enforces that output has a cosine similarity higher than the
    threshold with each of the comparisons supplied.
    """

    threshold: float
    comparisons: list[str]
    entity: str

    def _embed(self, comparisons) -> None:
        return np.fromiter(
            iter=EMBEDDING_MODEL.embed(comparisons),
            dtype=np.dtype((float, 384)),
        )

    def parse(self, text: str | AIMessage) -> str:
        if isinstance(text, AIMessage):
            text = text.content

        new = self._embed(text)
        old = self._embed(self.comparisons)

        cosines = cdist(XA=new, XB=old, metric='cosine')

        similar_comparisons: list[str] = []
        for comparison, cosine in zip(self.comparisons, cosines[0]):
            if cosine <= self.threshold:
                similar_comparisons.append(comparison)

        if len(similar_comparisons) > 0:
            similar_parsed = ', \n'.join(
                [f'"{similar}"' for similar in similar_comparisons]
            )
            LOG.info(
                f'Found {len(similar_comparisons)} cosine-similar '
                f'{self.entity} comparison(s)'
            )
            raise OutputParserException(
                f'SimilarityOutputParser expects the {self.entity} to be '
                'novel and unique. \n'
                f'Received: {text} \n'
                f'Similar to: {similar_parsed} \n'
                f'Give a novel and unique {self.entity}. '
                f"Can you create a {self.entity} that's completely different? "
                f'Return only the new {self.entity}. Do not explain. \n'
                f'{self.entity.title()}: '
            )

        return text

    @property
    def _type(self) -> str:
        return 'cosine_similarity_output_parser'


class LongestContinuousSimilarityOutputParser(BaseOutputParser[str]):
    """Custom similarity parser.

    Enforces that output has a longest continuous subsequence ratio lower than the
    threshold with each of the comparisons supplied.
    """

    threshold: float
    comparisons: list[str]
    entity: str

    def parse(self, text: str | AIMessage) -> str:
        if isinstance(text, AIMessage):
            text = text.content

        ratios = [
            SequenceMatcher(None, text, comparison).ratio()
            for comparison in self.comparisons
        ]

        similar_comparisons: list[str] = []
        for comparison, ratio in zip(self.comparisons, ratios):
            if ratio >= self.threshold:
                similar_comparisons.append(comparison)

        if len(similar_comparisons) > 0:
            similar_parsed = ', '.join(
                [f'"{similar}"' for similar in similar_comparisons]
            )
            LOG.info(
                f'Found {len(similar_comparisons)} continuous-similar '
                f'{self.entity} comparison(s)'
            )
            raise OutputParserException(
                'LongestContinuousSimilarityOutputParser expects {self.entity} to be '
                'novel and unique. \n'
                f'Received: "{text}" \n'
                f'Similar to: {similar_parsed} \n'
                f'Give a novel and unique {self.entity}. Be creative! '
                f'Return only the new {self.entity}. Do not explain. \n'
                f'{self.entity.title()}: '
            )

        return text

    @property
    def _type(self) -> str:
        return 'longest_subsequence_similarity_output_parser'


class LenOutputParser(BaseOutputParser[str]):
    """Custom similarity parser.

    Enforces that output has a length less than a certain number of characters.
    """

    max_len: int
    entity: str

    def parse(self, text: str | AIMessage) -> str:
        if isinstance(text, AIMessage):
            text = text.content
        if len(text) > self.max_len:
            LOG.info(
                f'Text of length {len(text)} higher than length {self.max_len} '
                'threshold'
            )
            raise OutputParserException(
                f'LenOutputParser expects the {self.entity} to be {self.max_len} '
                'characters or less \n'
                f'Received {self.entity} of length {len(text)} \n'
                f'You are a machine that generates {self.entity}. '
                f'Return only a {self.entity} of {self.max_len} '
                'characters or less. '
                'Do not apologise. Do not explain or annotate your correction. '
                f'Return only the {self.entity} and nothing else. \n'
                f'Shorter {self.entity}: '
            )

        return text

    def get_format_instructions(self) -> str:
        return f'Return only a {self.entity} of {self.max_len} ' 'characters or less. '

    @property
    def _type(self) -> str:
        return 'len_output_parser'


class IntOutputParser(BaseOutputParser[int]):
    """Custom parser. Enforces the output is an integer."""

    max_int: int
    min_int: int = 1

    def parse(self, text: str | AIMessage) -> str:
        if isinstance(text, AIMessage):
            text = text.content
        text = text.strip(punctuation + ' \n')
        text = re.search(r'\d+', text).group()
        try:
            return int(text)
        except ValueError as e:
            egs = {randrange(self.min_int, self.max_int + 1) for _ in range(5)}
            raise OutputParserException(
                'IntOutputParser expects an integer, not a string. '
                'Do not explain. Do not apologise. Return a number only. '
                f'Examples: {', '.join(map(str, egs))}. '
            ) from e

    def get_format_instructions(self) -> str:
        egs = {randrange(self.min_int, self.max_int + 1) for _ in range(5)}
        return (
            'Return an integer in numeric format. '
            f"Examples: {', '.join(map(str, egs))}."
        )

    @property
    def _type(self) -> str:
        return 'int_output_parser'


def strip_and_lower_parser(text: str | AIMessage) -> str:
    if isinstance(text, AIMessage):
        text = text.content

    return strip_and_lower(text)
