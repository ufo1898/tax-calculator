/**
 * 个税计算核心逻辑
 * 2024年起适用七级超额累进税率（月度）
 */

// 七级超额累进税率表（月度）
interface TaxBracket {
  maxAmount: number   // 级距上限（月）
  rate: number        // 税率
  quickDeduction: number // 速算扣除数
}

const TAX_BRACKETS: TaxBracket[] = [
  { maxAmount: 3000, rate: 0.03, quickDeduction: 0 },
  { maxAmount: 12000, rate: 0.10, quickDeduction: 210 },
  { maxAmount: 25000, rate: 0.20, quickDeduction: 1410 },
  { maxAmount: 35000, rate: 0.25, quickDeduction: 2660 },
  { maxAmount: 55000, rate: 0.30, quickDeduction: 4410 },
  { maxAmount: 80000, rate: 0.35, quickDeduction: 7160 },
  { maxAmount: Infinity, rate: 0.45, quickDeduction: 15160 },
]

// 起征点（月）
const TAX_THRESHOLD: number = 5000

// 社保费率
export class SocialInsurance {
  pension: number = 0.08      // 养老 8%
  medical: number = 0.02      // 医疗 2%
  unemployment: number = 0.002 // 失业 0.2%
  medicalFixed: number = 3    // 医疗固定 3元

  get totalRate(): number {
    return this.pension + this.medical + this.unemployment
  }

  calc(salary: number, baseSalary: number): number {
    // 社保按缴费基数算
    const base = baseSalary > 0 ? baseSalary : salary
    return base * this.totalRate + this.medicalFixed
  }
}

// 专项附加扣除（月度金额）
export interface SpecialDeduction {
  name: string
  amount: number    // 月扣除额
  selected: boolean
}

export const SPECIAL_DEDUCTIONS: SpecialDeduction[] = [
  { name: '子女教育', amount: 2000, selected: false },
  { name: '婴幼儿照护', amount: 2000, selected: false },
  { name: '继续教育', amount: 400, selected: false },
  { name: '住房贷款利息', amount: 1000, selected: false },
  { name: '住房租金', amount: 1500, selected: false },
  { name: '赡养老人', amount: 3000, selected: false },
]

// 公积金比例范围
export const HOUSING_FUND_RATES: number[] = [5, 6, 7, 8, 9, 10, 11, 12]

/**
 * 计算结果
 */
export interface TaxResult {
  salaryBeforeTax: number     // 税前工资
  socialInsurance: number     // 社保个人缴纳
  housingFund: number         // 公积金个人缴纳
  specialDeductionTotal: number // 专项附加扣除合计
  taxableIncome: number       // 应纳税所得额
  taxRate: number             // 适用税率
  quickDeduction: number      // 速算扣除数
  incomeTax: number           // 个人所得税
  salaryAfterTax: number      // 税后收入
  effectiveRate: number       // 实际税负率
  fiveInsuranceTotal: number  // 五险一金合计
}

/**
 * 计算个税
 */
export function calculateTax(
  salary: number,
  housingFundRate: number,    // 公积金比例 5-12
  socialBase: number,         // 社保缴费基数（0=按实际工资）
  selectedDeductions: SpecialDeduction[],
  si: SocialInsurance = new SocialInsurance()
): TaxResult {
  // 社保
  const socialIns = si.calc(salary, socialBase)

  // 公积金
  const baseForFund = socialBase > 0 ? socialBase : salary
  const housingFund = baseForFund * (housingFundRate / 100)

  // 专项附加扣除
  const deductionTotal = selectedDeductions
    .filter(d => d.selected)
    .reduce((sum, d) => sum + d.amount, 0)

  // 应纳税所得额
  const taxableIncome = Math.max(0, salary - socialIns - housingFund - TAX_THRESHOLD - deductionTotal)

  // 找税率档位
  let taxRate = 0
  let quickDed = 0
  for (const bracket of TAX_BRACKETS) {
    if (taxableIncome <= bracket.maxAmount) {
      taxRate = bracket.rate
      quickDed = bracket.quickDeduction
      break
    }
  }

  // 个税
  const incomeTax = Math.round(taxableIncome * taxRate - quickDed)

  const fiveTotal = socialIns + housingFund
  const salaryAfterTax = salary - fiveTotal - incomeTax

  return {
    salaryBeforeTax: salary,
    socialInsurance: Math.round(socialIns * 100) / 100,
    housingFund: Math.round(housingFund * 100) / 100,
    specialDeductionTotal: deductionTotal,
    taxableIncome: Math.round(taxableIncome * 100) / 100,
    taxRate: taxRate,
    quickDeduction: quickDed,
    incomeTax: incomeTax,
    salaryAfterTax: Math.round(salaryAfterTax * 100) / 100,
    effectiveRate: salary > 0 ? Math.round((incomeTax / salary) * 10000) / 100 : 0,
    fiveInsuranceTotal: Math.round(fiveTotal * 100) / 100
  }
}
