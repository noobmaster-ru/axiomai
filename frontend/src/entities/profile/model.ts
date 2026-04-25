export type ProfileInfoRow = {
  label: string;
  value: string;
};

export type Profile = {
  avatarUrl: string | null;
  fullName: string;
  hasTelegramData: boolean;
  infoRows: ProfileInfoRow[];
  initials: string;
  usernameLabel: string | null;
};
