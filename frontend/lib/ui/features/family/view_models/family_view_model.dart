import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../data/models/family_model.dart';
import '../../../../data/repositories/family_repository.dart';

class FamilyViewModel extends AsyncNotifier<FamilyModel?> {
  @override
  Future<FamilyModel?> build() async {
    return ref.read(familyRepositoryProvider).getMyFamily();
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(familyRepositoryProvider).getMyFamily(),
    );
  }

  Future<void> joinFamily(String inviteCode) async {
    final family = await ref.read(familyRepositoryProvider).joinFamily(inviteCode);
    state = AsyncValue.data(family);
  }
}

final familyViewModelProvider =
    AsyncNotifierProvider<FamilyViewModel, FamilyModel?>(
  FamilyViewModel.new,
);
