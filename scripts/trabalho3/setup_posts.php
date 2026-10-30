<?php
require '/var/www/html/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/media.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
$out = array();
foreach (array('imagem-1mb', 'texto-400kb', 'imagem-300kb') as $slug) {
    $marker = 'trabalho3-' . $slug;
    $existing = get_page_by_path($marker, OBJECT, 'post');
    if ($existing) { throw new Exception('Slug de teste existente: ' . $marker . '; verificar antes de repetir.'); }
    $data = array('post_title'=>'Trabalho 3 - ' . $slug, 'post_name'=>$marker, 'post_status'=>'publish', 'post_author'=>1);
    if ($slug === 'texto-400kb') {
        $seed = 'Teste academico de desempenho WordPress com Locust. Conteudo sintetico para comparar tempos de resposta entre uma, duas e tres instancias. ';
        $text = substr(str_repeat($seed, (int)ceil(409600 / strlen($seed))), 0, 409600);
        $data['post_content'] = '<p>' . $marker . '</p><p>' . $text . '</p>';
        $id = wp_insert_post($data, true);
        if (is_wp_error($id)) throw new Exception($id->get_error_message());
        $out[$slug] = array('id'=>$id, 'marker'=>$marker, 'text_bytes'=>strlen($text), 'content_bytes'=>strlen($data['post_content']));
    } else {
        $file = '/tmp/trabalho3-' . $slug . '.png';
        $aid = media_handle_sideload(array('name'=>'trabalho3-' . $slug . '.png', 'tmp_name'=>$file), 0, 'Imagem sintetica de teste ' . $slug);
        if (is_wp_error($aid)) throw new Exception($aid->get_error_message());
        $url = wp_get_attachment_url($aid);
        $data['post_content'] = '<p>' . $marker . '</p><img src="' . esc_url($url) . '" alt="Imagem sintetica de teste" />';
        $id = wp_insert_post($data, true);
        if (is_wp_error($id)) throw new Exception($id->get_error_message());
        wp_update_post(array('ID'=>$aid, 'post_parent'=>$id));
        $path = get_attached_file($aid);
        $out[$slug] = array('id'=>$id, 'marker'=>$marker, 'attachment_id'=>$aid, 'image_url'=>$url, 'bytes'=>filesize($path), 'sha256'=>hash_file('sha256', $path));
    }
}
echo json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
