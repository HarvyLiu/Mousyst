import { makeRecognizer } from './recognizer.mjs';
import vocabulary from './vocabulary.json';

import contractions from '../../../src/data/contractions.json';

const recognize = makeRecognizer(vocabulary.words, contractions);
self.onmessage = ({data}) => {
  self.postMessage({id: data.id, candidates: recognize(data.points)});
};
