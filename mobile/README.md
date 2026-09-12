# Bazaar Brief – mobile app (Expo / React Native)

Native app for Android and iOS. Reads the same JSON the website publishes
(`https://abhisheksi2o.github.io/Bazaarbrief/data/`), so it needs no login and no
server of its own. Stories, market ticker, fields, recap of the day and week, saved
stories, offline copy of the last edition, light and dark mode.

## Run it on your phone in two minutes (no store needed)

```
cd mobile
npm install
npx expo start
```
Install the **Expo Go** app from the Play Store / App Store, scan the QR code, and the
app opens on your phone with live data.

## Build store binaries (EAS Build, free tier)

One-time: create an account at https://expo.dev, then
```
npm install -g eas-cli
eas login
eas build:configure          # accept the defaults; writes eas.json (already included)
```

Android (Play Store needs an .aab):
```
eas build --platform android --profile production
```
iOS (App Store; needs an Apple Developer account, $99/year; EAS handles certificates):
```
eas build --platform ios --profile production
```
Test builds you can install directly: `eas build --platform android --profile preview` gives an .apk.

Submit from the command line once the store listings exist:
```
eas submit --platform android    # needs a Play Console service-account JSON
eas submit --platform ios        # needs App Store Connect API key
```

## Store checklist (things only the account owner can do)

- Google Play Console account ($25 one-time) and identity verification.
- Apple Developer Program ($99/year), App Store Connect app record.
- Privacy policy URL (the app stores only reading preferences on-device and calls no
  third-party services; a one-page policy stating that is enough).
- Store listing: name "Bazaar Brief", short description, screenshots (take them from
  Expo Go or a preview build), category News & Magazines.
- Content notes: news aggregator linking to publishers; recaps are AI-assisted and
  labelled "not investment advice".

## Layout

- `src/app/` – expo-router screens: `(tabs)/` Today, Fields, Recap, Markets, Saved; `story/[id]` modal; `field/[id]`.
- `src/lib/` – data fetching and caching (`data.ts`, `providers.tsx`), preferences (`store.ts`), theme tokens, formatting, section list.
- `src/components/` – masthead with ticker, story row, recap renderer, sparkline, small UI atoms.
- `assets/images/` – generated icons and splash.

Change `DATA_BASE` in `src/lib/data.ts` if the site moves.
