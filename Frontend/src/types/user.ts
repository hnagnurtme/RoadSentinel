export type UserRole = "admin" | "driver";

export interface UserProfile {
  id: string;
  email: string;
  name: string | null;
  role: UserRole;
  avatar_image_url: string | null;
  name__family: string | null;
  name__given: string | null;
  name__middle: string | null;
  name__prefix: string | null;
  name__suffix: string | null;
  birthday: string | null;
  gender: string | null;
  address__city: string | null;
  address__country: string | null;
  address__line1: string | null;
  address__line2: string | null;
}

export function mapUserFromApi(raw: Record<string, unknown>): UserProfile {
  const role = raw.role === "admin" ? "admin" : "driver";
  return {
    id: String(raw._id ?? ""),
    email: String(raw.email ?? ""),
    name: (raw.name as string | null) ?? null,
    role,
    avatar_image_url: (raw.avatar_image_url as string | null) ?? null,
    name__family: (raw.name__family as string | null) ?? null,
    name__given: (raw.name__given as string | null) ?? null,
    name__middle: (raw.name__middle as string | null) ?? null,
    name__prefix: (raw.name__prefix as string | null) ?? null,
    name__suffix: (raw.name__suffix as string | null) ?? null,
    birthday: raw.birthday ? String(raw.birthday) : null,
    gender: (raw.gender as string | null) ?? null,
    address__city: (raw.address__city as string | null) ?? null,
    address__country: (raw.address__country as string | null) ?? null,
    address__line1: (raw.address__line1 as string | null) ?? null,
    address__line2: (raw.address__line2 as string | null) ?? null,
  };
}