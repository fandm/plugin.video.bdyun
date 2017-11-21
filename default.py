#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Author is caasiu <caasiu@outlook.com> && source code is under GPLv3'''

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os, sys, re, json

__addon_id__= 'plugin.video.bdyun'
plugin_path = xbmcaddon.Addon(__addon_id__).getAddonInfo('path')
lib_path = os.path.join(plugin_path, 'resources', 'modules')
sys.path.append(lib_path)

from resources.modules import get_auth, pcs, utils, myplayer
from xbmcswift2 import Plugin, actions

plugin = Plugin()
dialog = xbmcgui.Dialog()


@plugin.route('/')
def main_menu():
    user_info = get_user_info()
    if user_info is None:
        items = [{
        'label': u'Войти',
        'path': plugin.url_for('login_dialog'),
        'is_playable': False
        }]
    else:
        items = [{
            'label': u'## Аккаунт: %s' %user_info['username'],
            'path': plugin.url_for('accout_setting'),
            'is_playable': False,
        },{
            'label': u'## Поиск',
            'path': plugin.url_for('search'),
            'is_playable': False
        },{
            'label': u'## Обновить',
            'path': plugin.url_for('refresh'),
            'is_playable': False
        }]

        for loopTime in range(0, 5):
            validation = pcs.token_validation(user_info['cookie'], user_info['tokens'])
            if validation:
                try:
                    homemenu = plugin.get_storage('homemenu')
                    if homemenu.get('item_list'):
                        item_list = homemenu.get('item_list')
                    else:
                        item_list = menu_cache(user_info['cookie'], user_info['tokens'])
                    items.extend(item_list)
                    break
                except (KeyError, TypeError, UnicodeError):
                    dialog.ok('Error', u'Ошибка запроса параметра', u'Войдите снова')
                    items.extend([{'label': u'Выйти и снова войти', 'path': plugin.url_for('clear_cache')}])
                    break
            else:
                cookie,tokens = get_auth.run(user_info['username'], user_info['password'])
                if tokens['bdstoken']:
                    save_user_info(user_info['username'], user_info['password'], cookie, tokens)
                else:
                    items.extend([{'label': u'Войти снова', 'path': plugin.url_for('relogin')}])
                    break

            if loopTime == 4:
                dialog.ok('Error', u'Неизвестная ошибка', u'Повторите попытку')
                items.extend([{'label': u'Войти снова', 'path': plugin.url_for('relogin')}])

    return plugin.finish(items, update_listing=True)


@plugin.route('/login_dialog/')
@plugin.route('/login_dialog/', name='relogin')
def login_dialog():
    username = dialog.input(u'Логин:', type=xbmcgui.INPUT_ALPHANUM)
    password = dialog.input(u'Пароль:', type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
    if username and password:
        cookie,tokens = get_auth.run(username,password)
        if tokens:
            save_user_info(username,password,cookie,tokens)
            homemenu = plugin.get_storage('homemenu')
            homemenu.clear()
            dialog.ok('',u'Успешный вход', u'Вернитесь на главную страницу и ждите...')
            items = [{'label': u'<< Вернуться на главную', 'path': plugin.url_for('main_menu')}]
            return plugin.finish(items, update_listing=True)
    else:
        dialog.ok('Error',u'Логин и Пароль не могут быть пустыми')
    return None


@plugin.route('/accout_setting/')
def accout_setting():
    user_info = get_user_info()
    items = [{
    'label': u'<< Вернуться на главную',
    'path': plugin.url_for('main_menu')
    },{
    'label': u'Выйти и очистить кеш',
    'path': plugin.url_for('clear_cache'),
    'is_playable': False
    },{
    'label': u'Войти снова / Войти',
    'path': plugin.url_for('relogin'),
    'is_playable': False
    },{
    'label': u'Настройки',
    'path': plugin.url_for('setting'),
    'is_playable': False
    }]
    if user_info:
        return plugin.finish(items, update_listing=True)
    else:
        return


@plugin.route('/setting/')
def setting():
    plugin.open_settings()


@plugin.route('/accout_setting/clear_cache/')
def clear_cache():
    info = plugin.get_storage('info')
    homemenu = plugin.get_storage('homemenu')
    pcs_info = plugin.get_storage('pcs_info')
    info.clear()
    homemenu.clear()
    pcs_info.clear()
    dialog.notification('', u'Очищено', xbmcgui.NOTIFICATION_INFO, 3000)
    xbmc.executebuiltin('Container.Refresh')
    return


@plugin.route('/search/')
def search():
    user_info = get_user_info()
    user_cookie = user_info['cookie']
    user_tokens = user_info['tokens']
    key = dialog.input(heading=u'Имя файла / Ключевое слово')
    if key:
        s = pcs.search(user_cookie, user_tokens, key)
        items = []
        if len(s['list']) == 1:
            for result in s['list']:
                if result['isdir'] == 1:
                    item = {
                            'label': result['server_filename'],
                            'path': plugin.url_for('directory', path=result['path'].encode('utf-8')),
                            'is_playable': False
                            }
                    items.append(item)
                elif result['category'] == 1:
                    if 'thumbs' in result and 'url2' in result['thumbs']:
                        ThumbPath = result['thumbs']['url2']
                        item = {
                                'label': result['server_filename'],
                                'path': plugin.url_for('quality', filepath=result['path'].encode('utf-8')),
                                'is_playable': False,
                                'icon': ThumbPath,
                                }
                    else:
                        item = {
                                'label': result['server_filename'],
                                'path': plugin.url_for('quality', filepath=result['path'].encode('utf-8')),
                                'is_playable': False,
                                }
                    items.append(item)
                elif result['category'] == 2:
                    item = {
                             'label': result['server_filename'],
                             'path': plugin.url_for('play_music', filepath=result['path'].encode('utf-8')),
                             'is_playable': False,
                            }
                    items.append(item)
            if items:
                return plugin.finish(items)
            else:
                dialog.ok('',u'Ничего не найдено')

        elif s['list']:
            for result in s['list']:
                if result['isdir'] == 1:
                    item = {
                            'label': result['path'],
                            'path': plugin.url_for('directory', path=result['path'].encode('utf-8')),
                            'is_playable': False
                            }
                    items.insert(0, item)
                elif result['category'] == 1:
                    if 'thumbs' in result and 'url2' in result['thumbs']:
                        ThumbPath = result['thumbs']['url2']
                        item = {
                                'label': result['path'],
                                'path': plugin.url_for('quality', filepath=result['path'].encode('utf-8')),
                                'is_playable': False,
                                'icon': ThumbPath,
                                }
                    else:
                        item = {
                                'label': result['path'],
                                'path': plugin.url_for('quality', filepath=result['path'].encode('utf-8')),
                                'is_playable': False,
                                }
                    items.append(item)
                elif result['category'] == 2:
                    item = {
                             'label': result['path'],
                             'path': plugin.url_for('play_music', filepath=result['path'].encode('utf-8')),
                             'is_playable': False,
                            }
                    items.append(item)
            if items:
                return plugin.finish(items)
            else:
                dialog.ok('',u'Ничего не найдено')

        else:
            dialog.ok('',u'Ничего не найдено')
            return None

    return


@plugin.route('/directory/<path>')
def directory(path):
    if isinstance(path, str):
        path = path.decode('utf-8')
    user_info = get_user_info()
    user_cookie = user_info['cookie']
    user_tokens = user_info['tokens']
    dir_files = pcs.list_dir_all(user_info['cookie'], user_info['tokens'], path)
    item_list = MakeList(dir_files)

    previous_path = os.path.dirname(path).encode('utf-8')
    if previous_path == '/':
        item_list.insert(0,{
                'label': u'<< Вернуться на главную',
                'path': plugin.url_for('main_menu')
            })
    else:
        item_list.insert(0,{
                'label': u'<< Назад',
                'path': plugin.url_for('directory', path=previous_path),
            })

    item_list.insert(0,{
                'label': u'## Текущий каталог: %s' % path,
                'path': plugin.url_for('refresh')
            })
    return plugin.finish(item_list, update_listing=True)


@plugin.route('/refresh/')
def refresh():
    homemenu = plugin.get_storage('homemenu')
    homemenu.clear()
    xbmc.executebuiltin('Container.Refresh')


@plugin.route('/quality/<filepath>')
def quality(filepath):
    if plugin.get_setting('show_stream_type', bool):
        stream_type = ['M3U8_AUTO_720', 'NONE']
        choice = dialog.select(u'Выберите качество', [u'Гладко',u'Оригинал'])
        if choice < 0:
            return
        elif choice == 0:
            stream = stream_type[choice]
        elif choice == 1:
            stream = False
    elif plugin.get_setting('stream_type', str) == 'NONE':
        stream = False
    else:
        stream = plugin.get_setting('stream_type', str)

    if isinstance(filepath, str):
        filepath = filepath.decode('utf-8')

    video_path = playlist_path(filepath, stream)

    name = os.path.basename(filepath)
    listitem = xbmcgui.ListItem(name)
    listitem.setInfo(type='Video', infoLabels={'Title': name})

    if video_path:
        xbmc.Player().play(video_path, listitem, windowed=False)


@plugin.route('/play_music/<filepath>')
def play_music(filepath):
    if isinstance(filepath, str):
        filepath = filepath.decode('utf-8')
    url = playlist_path(filepath, stream=False)
    name = os.path.basename(filepath)
    listitem = xbmcgui.ListItem(name)
    listitem.setInfo(type='Music', infoLabels={'Title': name})

    if url:
        xbmc.Player().play(url, listitem, windowed=False)


# cache the output of content menu
def menu_cache(cookie, tokens):
    pcs_files = pcs.list_dir_all(cookie, tokens, path='/')
    if pcs_files:
        item_list = MakeList(pcs_files)
    else:
        return [{'label': u'Нажмите обновить', 'path': plugin.url_for('refresh')}]
    homemenu = plugin.get_storage('homemenu', TTL=60)
    homemenu['item_list'] = item_list
    return item_list


def get_user_info():
    info = plugin.get_storage('info')
    user_info = info.get('user_info')
    return user_info


def save_user_info(username, password, cookie, tokens):
    info = plugin.get_storage('info')
    user_info = info.setdefault('user_info',{})
    user_info['username'] = username
    user_info['password'] = password
    user_info['cookie'] = cookie
    user_info['tokens'] = tokens
    info.sync()


def MakeList(pcs_files):
    item_list = []
    ContextMenu = [
        ('Поиск', actions.background(plugin.url_for('search'))),
        ('Обновить', actions.background(plugin.url_for('refresh'))),
        ('Очистить кеш', actions.background(plugin.url_for('clear_cache'))),
    ]
    for result in pcs_files:
        if result['isdir'] == 1:
            item = {
                    'label': result['server_filename'],
                    'path': plugin.url_for('directory', path=result['path'].encode('utf-8')),
                    'is_playable': False,
                    'context_menu': ContextMenu,
                    }
            item_list.append(item)
        elif result['category'] == 1:
            if 'thumbs' in result and 'url2' in result['thumbs']:
                ThumbPath = result['thumbs']['url2']
                item = {
                        'label': result['server_filename'],
                        'path': plugin.url_for('quality', filepath=result['path'].encode('utf-8')),
                        'is_playable': False,
                        'icon': ThumbPath,
                        'context_menu': ContextMenu,
                        }
            else:
                item = {
                        'label': result['server_filename'],
                        'path': plugin.url_for('quality', filepath=result['path'].encode('utf-8')),
                        'is_playable': False,
                        'context_menu': ContextMenu,
                        }
            item_list.append(item)
        elif result['category'] == 2:
            item = {
                    'label': result['server_filename'],
                    'path': plugin.url_for('play_music', filepath=result['path'].encode('utf-8')),
                    'is_playable': False,
                    'context_menu': ContextMenu,
                    }
            item_list.append(item)
    return item_list


def playlist_path(pcs_file_path, stream):
    user_info = get_user_info()
    user_name = user_info['username']
    user_cookie = user_info['cookie']
    user_tokens = user_info['tokens']

    if stream:
        playlist_data = pcs.get_streaming_playlist(user_cookie, pcs_file_path, stream)
        if playlist_data:
            raw_dir = os.path.dirname(pcs_file_path)
            m = re.search('\/(.*)', raw_dir)
            dirname = m.group(1)
            basename = os.path.basename(pcs_file_path)
            r = re.search('(.*)\.(.*)$', basename)
            filename = ''.join([r.group(1), stream, '.m3u8'])
            dirpath = os.path.join(utils.data_dir(), user_name, dirname)
            if not xbmcvfs.exists(dirpath):
                xbmcvfs.mkdirs(dirpath)
            filepath = os.path.join(dirpath, filename)
            tmpFile = xbmcvfs.File(filepath, 'w')
            tmpFile.write(bytearray(playlist_data, 'utf-8'))
            return filepath
        else:
            dialog.notification('', u'Не удалось открыть видео', xbmcgui.NOTIFICATION_INFO, 4000)
            return None
    else:
        url = pcs.stream_download(user_cookie, user_tokens, pcs_file_path)
        if url:
            return url
        else:
            dialog.notification('', u'Не удаётся использовать режим Оригинал, попробуйте режим Гладко', xbmcgui.NOTIFICATION_INFO, 4000)
            return None


if __name__ == '__main__':
    plugin.run()
