import { makeRecognizer } from './recognizer.mjs';
import vocabulary from './vocabulary.json';

const recognize = makeRecognizer(vocabulary.words);
self.onmessage = ({data}) => {
  self.postMessage({id: data.id, candidates: recognize(data.points)});
};
