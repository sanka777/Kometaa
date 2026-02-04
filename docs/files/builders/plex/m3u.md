---
hide:
  - toc
---
# Plex M3U

Construit une collection ou une playlist à partir d'un fichier `.m3u` en mappant chaque entrée vers un item Plex.

## Format attendu

Kometa lit le fichier `.m3u` ligne par ligne. Les commentaires (lignes qui commencent par `#`) sont ignorés, sauf `#EXTINF` qui fournit un titre pour l'entrée suivante.

Types de lignes supportés :

| Type de ligne | Exemple | Résultat |
|:--|:--|:--|
| Chemin local | `/media/Movies/Alien (1979)/Alien.mkv` | Recherche par chemin Plex (`item.locations`) |
| URL Plex avec rating key | `https://app.plex.tv/desktop/#!/server/.../details?key=/library/metadata/12345` | Extraction directe du rating key `12345` |
| URL de fichier | `file:///media/Movies/Alien (1979)/Alien.mkv` | Traitée comme chemin local |
| Titre | `Alien (1979)` | Recherche exacte par titre (et année optionnelle) |
| URL non Plex | `https://example.com/Alien.mkv` | Utilise le titre `#EXTINF` si disponible, sinon le nom de fichier |

### Logique de mapping

1. Si la ligne contient un `ratingKey` Plex (ex. `/library/metadata/12345`), il est utilisé directement.
2. Sinon, si la ligne est un chemin local (ou `file://`), Kometa cherche un item avec ce chemin dans `item.locations`.
3. Sinon, Kometa effectue une recherche exacte par titre (et année si fournie entre parenthèses).

## Exemple

```yaml
collections:
  Mes Films M3U:
    m3u: /data/playlists/films.m3u
```

```m3u
#EXTM3U
#EXTINF:-1,Alien (1979)
/media/Movies/Alien (1979)/Alien.mkv
#EXTINF:-1,Blade Runner (1982)
https://app.plex.tv/desktop/#!/server/xxxxx/details?key=/library/metadata/67890
```

{%
    include-markdown "./sort-options.md"
%}
