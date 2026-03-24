import type { Profile, ProfileInfoRow } from "../../entities/profile/model";
import { getTelegramUser } from "../../theme/telegram";

function buildFullName(firstName?: string, lastName?: string) {
  const value = [firstName?.trim(), lastName?.trim()].filter(Boolean).join(" ");
  return value || null;
}

function buildInitials(fullName: string, username?: string) {
  const source = fullName || username || "AxiomAI";

  return source
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "AI";
}

function buildInfoRows(user: TelegramWebAppUser | null): ProfileInfoRow[] {
  if (!user) {
    return [
      {
        label: "Источник",
        value: "Откройте мини-приложение внутри Telegram, чтобы увидеть профиль.",
      },
    ];
  }

  const rows: ProfileInfoRow[] = [];

  if (user.id) {
    rows.push({
      label: "Telegram ID",
      value: String(user.id),
    });
  }

  if (user.language_code) {
    rows.push({
      label: "Язык",
      value: user.language_code.toUpperCase(),
    });
  }

  rows.push({
    label: "Telegram",
    value: user.is_premium ? "Premium" : "Обычный аккаунт",
  });

  return rows;
}

export function getTelegramProfile(): Profile {
  const user = getTelegramUser();
  const fullName = buildFullName(user?.first_name, user?.last_name) ?? user?.username ?? "Профиль Telegram";
  const usernameLabel = user?.username ? `@${user.username}` : null;

  return {
    avatarUrl: user?.photo_url ?? null,
    fullName,
    hasTelegramData: Boolean(user),
    infoRows: buildInfoRows(user),
    initials: buildInitials(fullName, user?.username),
    usernameLabel,
  };
}
