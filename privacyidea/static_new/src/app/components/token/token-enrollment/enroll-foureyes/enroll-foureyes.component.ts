import {
  Component,
  computed,
  EventEmitter,
  inject,
  OnInit,
  Output,
  Signal,
} from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatCheckbox } from '@angular/material/checkbox';
import {
  ErrorStateMatcher,
  MatOption,
  MatOptionSelectionChange,
} from '@angular/material/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatError, MatSelect } from '@angular/material/select';
import {
  RealmService,
  RealmServiceInterface,
} from '../../../../services/realm/realm.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';

import { Observable, of } from 'rxjs';
import { FourEyesApiPayloadMapper } from '../../../../mappers/token-api-payload/4eyes-token-api-payload.mapper';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';

export interface FourEyesEnrollmentOptions extends TokenEnrollmentData {
  type: '4eyes';
  separator: string;
  requiredTokenOfRealms: { realm: string; tokens: number }[];
  onlyAddToRealm: boolean;
  userRealm?: string;
}

export class RequiredRealmsErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid =
      control && control.value ? control.value.length === 0 : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: 'app-enroll-foureyes',
  standalone: true,
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
export class EnrollFoureyesComponent implements OnInit {
  protected readonly enrollmentMapper: FourEyesApiPayloadMapper = inject(
    FourEyesApiPayloadMapper,
  );
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === '4eyes')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  separatorControl = new FormControl<string>(':', [Validators.required]);
  requiredTokensOfRealmsControl = new FormControl<
    { realm: string; tokens: number }[]
  >([], [Validators.required, Validators.minLength(1)]);
  onlyAddToRealmControl = new FormControl<boolean>(false, [
    Validators.required,
  ]);

  foureyesForm = new FormGroup({
    separator: this.separatorControl,
    requiredTokensOfRealms: this.requiredTokensOfRealmsControl,
    onlyAddToRealm: this.onlyAddToRealmControl,
  });

  realmOptions = this.realmService.realmOptions;
  tokenCountMapping: Signal<Record<string, number>> = computed(() => {
    const realms = this.requiredTokensOfRealmsControl.value;
    if (!realms) {
      return {};
    }
    return realms.reduce(
      (acc, curr) => {
        acc[curr.realm] = curr.tokens;
        return acc;
      },
      {} as Record<string, number>,
    );
  });
  requiredRealmsErrorStateMatcher = new RequiredRealmsErrorStateMatcher();

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({
      separator: this.separatorControl,
      requiredTokensOfRealms: this.requiredTokensOfRealmsControl,
      onlyAddToRealm: this.onlyAddToRealmControl,
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  getTokenCount(realm: string): number {
    const tokensArray = this.requiredTokensOfRealmsControl.value;
    if (!tokensArray) return 0;
    const tokenObj = tokensArray.find((item) => item.realm === realm);
    return tokenObj ? tokenObj.tokens : 0;
  }

  updateTokenCount(realm: string, tokens: number): void {
    let tokensArray = this.requiredTokensOfRealmsControl.value;
    if (!tokensArray) tokensArray = [];

    const index = tokensArray.findIndex((item) => item.realm === realm);
    if (index > -1) {
      if (tokens === 0) {
        this.removeRealmFromSelection(tokensArray, index);
      } else {
        tokensArray[index] = { realm, tokens };
      }
    } else {
      if (tokens > 0) {
        this.addRealmToSelection(tokensArray, realm, tokens);
      }
    }
    this.requiredTokensOfRealmsControl.setValue([...tokensArray]);
    this.requiredTokensOfRealmsControl.markAsDirty();
    this.requiredTokensOfRealmsControl.updateValueAndValidity();
  }

  private removeRealmFromSelection(
    tokensArray: { realm: string; tokens: number }[],
    index: number,
  ): void {
    tokensArray.splice(index, 1);
  }

  private addRealmToSelection(
    tokensArray: { realm: string; tokens: number }[],
    realm: string,
    tokens: number,
  ): void {
    tokensArray.push({ realm, tokens });
  }

  onRealmSelectionChange(event: MatOptionSelectionChange, realm: string): void {
    if (event.isUserInput && event.source.selected) {
      if (this.getTokenCount(realm) === 0) {
        this.updateTokenCount(realm, 1);
      }
    } else if (event.isUserInput && !event.source.selected) {
      this.updateTokenCount(realm, 0);
    }
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse | null> => {
    if (this.foureyesForm.invalid) {
      this.foureyesForm.markAllAsTouched();
      return of(null);
    }
    const enrollmentData: FourEyesEnrollmentOptions = {
      ...basicOptions,
      type: '4eyes',
      separator: this.separatorControl.value ?? ':',
      requiredTokenOfRealms: this.requiredTokensOfRealmsControl.value ?? [],
      onlyAddToRealm: !!this.onlyAddToRealmControl.value,
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper,
    });
  };
}
