import { publicSpeakerName } from './rules.mjs';
import { config } from './config.mjs';

export const STATUS_LABEL = {
  presale: 'Предпродажа',
  scheduled: 'Дата назначена',
  done: 'Прошёл',
  waitlist: 'Лист ожидания',
};

export function webinarView(data) {
  const speaker = publicSpeakerName(data.speaker);
  const paymentUrl = data.payment_url || config.webinar_payment_url || null;
  const canPay = (data.status === 'presale' || data.status === 'scheduled') && Boolean(paymentUrl);
  return { speaker, paymentUrl, canPay, statusLabel: STATUS_LABEL[data.status] };
}
