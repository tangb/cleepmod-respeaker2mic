/**
 * Respeaker2mic service
 * Handle respeaker2mic module requests
 */
var respeaker2micService = function($q, rpcService, raspiotService) {
    var self = this;

    self.addLedsProfile = function(name, repeat, actions)
    {
        return rpcService.sendCommand('add_leds_profile', 'respeaker2mic', {'name':name, 'repeat':repeat, 'actions':actions})
            .then(function() {
                return raspiotService.reloadModuleConfig('respeaker2mic');
            });
    };

    self.removeLedsProfile = function(uuid)
    {
        return rpcService.sendCommand('remove_leds_profile', 'respeaker2mic', {'profile_uuid':uuid})
            .then(function() {
                return raspiotService.reloadModuleConfig('respeaker2mic');
            });
    };

    self.testLedsProfile = function(uuid)
    {
        return rpcService.sendCommand('test_leds_profile', 'respeaker2mic', {'profile_uuid':uuid});
    };

};
    
var RaspIot = angular.module('RaspIot');
RaspIot.service('respeaker2micService', ['$q', 'rpcService', 'raspiotService', respeaker2micService]);

