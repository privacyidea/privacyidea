import {
  Component,
  computed,
  Input,
  Signal,
  signal,
  WritableSignal,
} from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { RealmService } from '../../../../services/realm/realm.service';
import { MatOption, MatOptionSelectionChange } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';

@Component({
  selector: 'app-enroll-foureyes',
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatOption,
    MatSelect,
  ],
  templateUrl: './enroll-foureyes.component.html',
  styleUrl: './enroll-foureyes.component.scss',
})
export class EnrollFoureyesComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === '4eyes')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() separator!: WritableSignal<string>;
  @Input() requiredTokensOfRealm!: WritableSignal<
    { realm: string; tokens: number }[]
  >;
  requiredRealms = signal<string[]>([]);
  realmOptions = signal<string[]>([]);
  tokenCountMapping: Signal<Record<string, number>> = computed(() => {
    return this.requiredTokensOfRealm().reduce(
      (acc, curr) => {
        acc[curr.realm] = curr.tokens;
        return acc;
      },
      {} as Record<string, number>,
    );
  });

  constructor(private realmService: RealmService) {}

  ngOnInit(): void {
    this.realmService.getRealms().subscribe((response) => {
      this.realmOptions.set(Object.keys(response.result.value));
    });
  }

  getTokenCount(realm: string): number {
    const tokensArray = this.requiredTokensOfRealm();
    const tokenObj = tokensArray.find((item) => item.realm === realm);
    return tokenObj ? tokenObj.tokens : 0;
  }

  updateTokenCount(realm: string, tokens: number): void {
    const tokensArray = this.requiredTokensOfRealm();
    const index = tokensArray.findIndex((item) => item.realm === realm);
    if (index > -1) {
      tokensArray[index] = { realm, tokens };
    } else {
      tokensArray.push({ realm, tokens });
    }
    this.requiredTokensOfRealm.set([...tokensArray]);
  }

  onRealmSelectionChange(event: MatOptionSelectionChange, realm: string): void {
    if (event.isUserInput && event.source.selected) {
      if (this.getTokenCount(realm) === 0) {
        this.updateTokenCount(realm, 1);
      }
    }
  }
}
