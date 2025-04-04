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
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RealmService } from '../../../../services/realm/realm.service';
import {
  ErrorStateMatcher,
  MatOption,
  MatOptionSelectionChange,
} from '@angular/material/core';
import { MatError, MatSelect } from '@angular/material/select';
import { MatCheckbox } from '@angular/material/checkbox';
import { TokenService } from '../../../../services/token/token.service';

export class RequiredRealmsErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid =
      control && control.value ? control.value.length === 0 : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

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
    MatCheckbox,
    MatError,
  ],
  templateUrl: './enroll-foureyes.component.html',
  styleUrl: './enroll-foureyes.component.scss',
})
export class EnrollFoureyesComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === '4eyes')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() separator!: WritableSignal<string>;
  @Input() requiredTokensOfRealms!: WritableSignal<
    { realm: string; tokens: number }[]
  >;
  @Input() onlyAddToRealm!: WritableSignal<boolean>;

  requiredRealms = signal<string[]>([]);
  realmOptions = signal<string[]>([]);
  tokenCountMapping: Signal<Record<string, number>> = computed(() => {
    return this.requiredTokensOfRealms().reduce(
      (acc, curr) => {
        acc[curr.realm] = curr.tokens;
        return acc;
      },
      {} as Record<string, number>,
    );
  });
  requiredRealmsErrorStateMatcher = new RequiredRealmsErrorStateMatcher();

  constructor(
    private realmService: RealmService,
    private tokenService: TokenService,
  ) {}

  ngOnInit(): void {
    this.realmService.getRealms().subscribe((response) => {
      this.realmOptions.set(Object.keys(response.result.value));
    });
  }

  getTokenCount(realm: string): number {
    const tokensArray = this.requiredTokensOfRealms();
    const tokenObj = tokensArray.find((item) => item.realm === realm);
    return tokenObj ? tokenObj.tokens : 0;
  }

  updateTokenCount(realm: string, tokens: number): void {
    const tokensArray = this.requiredTokensOfRealms();
    const index = tokensArray.findIndex((item) => item.realm === realm);
    if (index > -1) {
      tokensArray[index] = { realm, tokens };
    } else {
      tokensArray.push({ realm, tokens });
    }
    this.requiredTokensOfRealms.set([...tokensArray]);
  }

  onRealmSelectionChange(event: MatOptionSelectionChange, realm: string): void {
    if (event.isUserInput && event.source.selected) {
      if (this.getTokenCount(realm) === 0) {
        this.updateTokenCount(realm, 1);
      }
    }
  }
}
