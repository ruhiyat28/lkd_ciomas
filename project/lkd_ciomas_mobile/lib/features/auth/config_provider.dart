import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';

class AppConfig {
  final List<Map<String, String>> desaList;
  final Map<String, String> lembaga;
  final List<int> tenorOptions;

  AppConfig({
    required this.desaList,
    required this.lembaga,
    required this.tenorOptions,
  });
}

class ConfigNotifier extends StateNotifier<AppConfig?> {
  final ApiClient _api;
  ConfigNotifier(this._api) : super(null);

  Future<void> loadConfig() async {
    try {
      final res = await _api.get(ApiEndpoints.config);
      final data = res.data['data'];
      final desaList = (data['desa_list'] as List)
          .map((e) => {
                'kode': e['kode'] as String,
                'nama': e['nama'] as String,
              })
          .toList();
      final lembaga = Map<String, String>.from(data['lembaga'] as Map);
      final tenorOptions = (data['tenor_options'] as List)
          .map((e) => (e is int) ? e : int.tryParse(e.toString()) ?? 0)
          .where((e) => e > 0)
          .toList();
      state = AppConfig(
          desaList: desaList, lembaga: lembaga, tenorOptions: tenorOptions);
    } catch (_) {}
  }
}

final configProvider =
    StateNotifierProvider<ConfigNotifier, AppConfig?>((ref) {
  final api = ref.watch(apiClientProvider);
  return ConfigNotifier(api);
});
