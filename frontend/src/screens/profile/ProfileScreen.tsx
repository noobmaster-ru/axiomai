import { getTelegramProfile } from "../../shared/telegram/profile";
import "./ProfileScreen.css";

export function ProfileScreen() {
  const profile = getTelegramProfile();

  return (
    <div className="profile-screen">
      <section className="profile-screen__hero">
        <div className="profile-screen__hero-head">
          {profile.avatarUrl ? (
            <img
              className="profile-screen__avatar"
              src={profile.avatarUrl}
              alt={profile.fullName}
            />
          ) : (
            <div className="profile-screen__avatar profile-screen__avatar--fallback" aria-hidden="true">
              {profile.initials}
            </div>
          )}

          <div className="profile-screen__identity">
            <h2 className="profile-screen__name">{profile.fullName}</h2>
            {profile.usernameLabel ? (
              <span className="profile-screen__username">{profile.usernameLabel}</span>
            ) : null}
          </div>
        </div>
      </section>

      <section className="profile-screen__section">
        <div className="profile-screen__section-header">
          <h3 className="profile-screen__section-title">Информация профиля</h3>
        </div>

        <div className="profile-screen__info-list">
          {profile.infoRows.map((row) => (
            <div className="profile-screen__info-row" key={row.label}>
              <span className="profile-screen__info-label">{row.label}</span>
              <span className="profile-screen__info-value">{row.value}</span>
            </div>
          ))}
        </div>
      </section>

      {!profile.hasTelegramData ? (
        <section className="profile-screen__section">
          <div className="profile-screen__note-card">
            <p className="profile-screen__note-text">Откройте приложение внутри Telegram.</p>
          </div>
        </section>
      ) : null}
    </div>
  );
}
