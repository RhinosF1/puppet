"use strict";

exports.setup = function( parsoidConfig ) {
	// wiki end points
	parsoidConfig.setInterwiki( 'allthetropeswiki', 'https://allthetropes.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'aryamanwiki', 'https://aryaman.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'cbmediawiki', 'https://cbmedia.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'cinemawiki', 'https://cinema.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'clicordiwiki', 'https://clicordi.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'extloadwiki', 'https://extload.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'genwiki', 'https://gen.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'mecanonwiki', 'https://mecanon.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'metawiki', 'https://meta.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'nwpwiki', 'https://nwp.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'pqwiki', 'https://pq.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'permanentfuturelabwiki', 'https://permanentfuturelab.wiki/w/api.php')
	parsoidConfig.setInterwiki( 'rawdatawiki', 'https://rawdata.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'recherchesdocumentaireswiki', 'https://recherchesdocumentaires.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'spiralwiki', 'https://spiral.wiki/w/api.php' );
	parsoidConfig.setInterwiki( 'torejorgwiki', 'https://torejorg.miraheze.org/w/api.php' );
	parsoidConfig.setInterwiki( 'unikumwiki', 'https://unikum.miraheze.org/w/api.php' );

	// Don't load WMF wikis
	parsoidConfig.loadWMF = false;
	parsoidConfig.defaultWiki = 'metawiki';

	// Enable debug mode (prints extra debugging messages)
	parsoidConfig.debug = false;

	parsoidConfig.usePHPPreProcessor = true;

	// Use selective serialization (default false)
	parsoidConfig.useSelser = true;
};
